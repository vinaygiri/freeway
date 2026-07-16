"""Shared provider execution primitive for API product handlers."""

from __future__ import annotations

import contextlib
import json
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi import HTTPException
from loguru import logger

from config.settings import Settings
from core.anthropic import (
    get_token_count,
    iter_provider_top_level_error_sse_events,
)
from core.quota import QuotaTracker
from core.trace import api_messages_request_snapshot, trace_event, traced_async_stream
from providers.base import BaseProvider
from providers.exceptions import (
    APIError,
    AuthenticationError,
    InvalidRequestError,
    OverloadedError,
    ProviderError,
    RateLimitError,
    ServiceUnavailableError,
    blocks_provider,
    should_failover,
)

from .model_router import ResolvedModel, RoutedMessagesRequest
from .router_policy import RoutingPolicy

_AUTH_HTTP_STATUSES = frozenset({401, 403})

# Peek at most this many lead SSE chunks (message_start / ping) while deciding
# whether a candidate connected successfully — bounded so a chatty-but-silent
# provider can't stall the response indefinitely.
_PEEK_MAX_CHUNKS = 64


def _classify_sse_chunk(chunk: str) -> str:
    """Classify a raw Anthropic SSE chunk as 'content', 'error', or 'other'.

    'content'/'error' are terminal peek signals (commit vs fail over); 'other'
    (message_start, ping) keeps peeking. Errors are detected pre-content only —
    once 'content' is seen the peek commits, so a mid-stream error is never here.
    """
    lowered = chunk.lower()
    if (
        "event: error" in lowered
        or '"type":"error"' in lowered
        or '"type": "error"' in lowered
    ):
        return "error"
    if (
        "content_block_start" in lowered
        or "content_block_delta" in lowered
        or ("message_delta" in lowered and "stop_reason" in lowered)
    ):
        return "content"
    return "other"


def _error_from_sse(chunk: str) -> ProviderError:
    """Build a typed ProviderError from a pre-content SSE `error` event so the
    failover loop can classify it (auth → block, 400 → terminal, else → failover)."""
    message = "provider returned an error"
    error_type = ""
    for line in chunk.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        try:
            payload = json.loads(line[5:].strip())
        except ValueError:
            continue
        err = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(err, dict):
            message = str(err.get("message") or message)[:300]
            error_type = str(err.get("type") or "")
            break
    if error_type == "authentication_error":
        return AuthenticationError(message)
    if error_type == "rate_limit_error":
        return RateLimitError(message)
    if error_type == "overloaded_error":
        return OverloadedError(message)
    if error_type == "invalid_request_error":
        return InvalidRequestError(message)
    return APIError(message, status_code=500)


async def _aclose(iterator: AsyncIterator[str]) -> None:
    """Best-effort close of a peeked-then-abandoned upstream stream (no leak)."""
    aclose = getattr(iterator, "aclose", None)
    if aclose is not None:
        with contextlib.suppress(Exception):
            await aclose()


async def _peek_stream(
    iterator: AsyncIterator[str],
) -> tuple[list[str], ProviderError | None]:
    """Pull opening chunks until content (commit) or a pre-content error (fail over).

    Returns (buffered_chunks, connect_error). connect_error is None when the stream
    produced content, ended cleanly, or hit the peek cap — i.e. the candidate is
    usable and the buffered chunks should be replayed before the rest.
    """
    buffered: list[str] = []
    try:
        async for chunk in iterator:
            buffered.append(chunk)
            kind = _classify_sse_chunk(chunk)
            if kind == "error":
                return buffered, _error_from_sse(chunk)
            if kind == "content" or len(buffered) >= _PEEK_MAX_CHUNKS:
                return buffered, None
    except ProviderError as exc:
        return buffered, exc
    except Exception as exc:
        return buffered, APIError(str(exc) or type(exc).__name__)
    return buffered, None  # ended with no content and no error (empty completion)


async def _replay(chunks: list[str]) -> AsyncIterator[str]:
    """Re-serve already-buffered chunks (a provider's streamed error) with no
    upstream still attached."""
    for chunk in chunks:
        yield chunk


async def _prepend(first: list[str], rest: AsyncIterator[str]) -> AsyncIterator[str]:
    """Yield already-peeked chunks, then the remaining stream, closing it on exit
    (the `finally` prevents a leaked upstream connection on client disconnect)."""
    try:
        for chunk in first:
            yield chunk
        async for chunk in rest:
            yield chunk
    finally:
        aclose = getattr(rest, "aclose", None)
        if aclose is not None:
            await aclose()


TokenCounter = Callable[[list[Any], str | list[Any] | None, list[Any] | None], int]
ProviderGetter = Callable[[str], BaseProvider]


class ProviderExecutionService:
    """Resolve a provider and execute one routed Anthropic Messages stream."""

    def __init__(
        self,
        settings: Settings,
        provider_getter: ProviderGetter,
        *,
        token_counter: TokenCounter = get_token_count,
        quota_tracker: QuotaTracker | None = None,
        routing_policy: RoutingPolicy | None = None,
    ) -> None:
        self._settings = settings
        self._provider_getter = provider_getter
        self._token_counter = token_counter
        self._quota_tracker = quota_tracker
        self._routing_policy = routing_policy or RoutingPolicy()

    async def stream_with_failover(
        self,
        primary: RoutedMessagesRequest,
        fallbacks: list[ResolvedModel],
        *,
        wire_api: str,
        raw_log_label: str,
        raw_log_payload: Any,
    ) -> AsyncIterator[str]:
        """Stream the first candidate that connects, failing over to the next.

        Candidates (primary + fallbacks) are ordered by the routing policy
        (skipping circuit-open / quota-exhausted / dead-health providers). For each
        we run eager preflight, then **peek the opening chunks** to detect a
        connect-time failure (rate limit / overload / 5xx / auth) *before* the
        response commits — so it fails over to the next model with zero content
        lost, and records the failure so the circuit learns. Only a malformed
        request (400) is terminal (fails identically everywhere).
        """
        policy = self._routing_policy
        required_tokens = self._token_counter(
            primary.request.messages,
            primary.request.system,
            primary.request.tools,
        )
        candidates = policy.order(
            [primary.resolved, *fallbacks], required_tokens=required_tokens
        )
        blocked_providers: set[str] = set()
        last_error: ProviderError | None = None
        # A candidate that opened a stream but failed *at connect* (pre-content),
        # streaming a replayable error event. Kept so the client gets that provider's
        # real error verbatim if nothing else connects.
        held_buffered: list[str] | None = None
        held_resolved: ResolvedModel | None = None
        # True once any candidate got past eager preflight and into the peek — i.e.
        # a stream actually opened. Distinguishes "connected then failed" (render a
        # graceful error stream) from "nothing ever started" (raise so the handler
        # returns a proper HTTP error).
        stream_opened = False
        attempts = 0
        for resolved in candidates:
            if attempts >= policy.max_attempts:
                break
            if resolved.provider_id in blocked_providers:
                continue
            attempts += 1
            routed = self._routed_for(primary, resolved)

            # 1) Eager preflight (provider lookup + request build).
            try:
                iterator = self.stream(
                    routed,
                    wire_api=wire_api,
                    raw_log_label=raw_log_label,
                    raw_log_payload=raw_log_payload,
                )
            except ProviderError as exc:
                last_error = self._note_failure(
                    policy, resolved, exc, blocked_providers
                )
                if not should_failover(exc):
                    break
                continue
            except HTTPException as exc:
                if exc.status_code in _AUTH_HTTP_STATUSES:
                    blocked_providers.add(resolved.provider_id)
                policy.record_failure(resolved)
                last_error = APIError(str(exc.detail), status_code=exc.status_code)
                continue

            # 2) Peek the opening chunks to catch a connect-time error. A re-raised
            #    transport error surfaces here as connect_error with no buffered
            #    chunks; a provider that *streams* an error event surfaces it as
            #    connect_error with those chunks buffered (replayable).
            stream_opened = True
            buffered, connect_error = await _peek_stream(iterator)

            if connect_error is not None:
                await _aclose(iterator)
                last_error = self._note_failure(
                    policy, resolved, connect_error, blocked_providers
                )
                if buffered:
                    held_buffered, held_resolved = buffered, resolved
                if not should_failover(connect_error):
                    break
                continue

            # 3) Connected — commit this candidate.
            policy.record_success(resolved)
            policy.record_request(
                primary=primary.resolved,
                served=resolved,
                gateway_model=primary.request.model,
                input_tokens=required_tokens,
                candidates_tried=attempts,
                outcome="routed",
                required_tokens=required_tokens,
            )
            return _prepend(buffered, iterator)

        # No candidate connected.
        # (a) A provider streamed a real error event — replay it verbatim so the
        #     client gets that provider's exact error (502 / response.failed / etc.).
        if held_buffered is not None:
            policy.record_request(
                primary=primary.resolved,
                served=held_resolved,
                gateway_model=primary.request.model,
                input_tokens=required_tokens,
                candidates_tried=attempts,
                outcome="error",
                error=last_error.message if last_error is not None else None,
                required_tokens=required_tokens,
            )
            return _replay(held_buffered)
        # (b) A stream opened but failed pre-content by *raising* (real transports) —
        #     synthesize a detectable top-level error so failover stays graceful.
        if stream_opened and last_error is not None:
            policy.record_request(
                primary=primary.resolved,
                served=None,
                gateway_model=primary.request.model,
                input_tokens=required_tokens,
                candidates_tried=attempts,
                outcome="error",
                error=last_error.message,
                required_tokens=required_tokens,
            )
            return self._error_stream(primary.request, required_tokens, last_error)
        # (c) Nothing ever started (all eager failures / no candidates) — raise.
        policy.record_request(
            primary=primary.resolved,
            served=None,
            gateway_model=primary.request.model,
            input_tokens=required_tokens,
            candidates_tried=attempts,
            outcome="eager_error" if last_error is not None else "no_candidates",
            error=last_error.message if last_error is not None else None,
            required_tokens=required_tokens,
        )
        if last_error is not None:
            raise last_error
        raise ServiceUnavailableError("No routable model candidates available")

    async def _error_stream(
        self, request: Any, input_tokens: int, error: ProviderError
    ) -> AsyncIterator[str]:
        """Render an exhausted-failover failure as a single top-level Anthropic error
        event so downstream error handling (chat 502, responses ``response.failed``,
        native error rendering) fires — used when a provider failed by *raising*
        (no replayable error stream)."""
        for chunk in iter_provider_top_level_error_sse_events(
            request=request,
            input_tokens=input_tokens,
            error_message=error.message,
            log_raw_sse_events=self._settings.log_raw_api_payloads,
        ):
            yield chunk

    @staticmethod
    def _note_failure(
        policy: RoutingPolicy,
        resolved: ResolvedModel,
        exc: ProviderError,
        blocked_providers: set[str],
    ) -> ProviderError:
        """Record a candidate failure (circuit) and block the provider on auth."""
        policy.record_failure(resolved)
        if blocks_provider(exc):
            blocked_providers.add(resolved.provider_id)
        return exc

    @staticmethod
    def _routed_for(
        primary: RoutedMessagesRequest, resolved: ResolvedModel
    ) -> RoutedMessagesRequest:
        if resolved is primary.resolved:
            return primary
        request = primary.request.model_copy(deep=True)
        request.model = resolved.provider_model
        return RoutedMessagesRequest(request=request, resolved=resolved)

    def stream(
        self,
        routed: RoutedMessagesRequest,
        *,
        wire_api: str,
        raw_log_label: str,
        raw_log_payload: Any,
    ) -> AsyncIterator[str]:
        provider = self._provider_getter(routed.resolved.provider_id)
        provider.preflight_stream(
            routed.request,
            thinking_enabled=routed.resolved.thinking_enabled,
        )

        route_trace: dict[str, Any] = {
            "stage": "routing",
            "event": "api.route.resolved",
            "source": "api",
            "provider_id": routed.resolved.provider_id,
            "provider_model": routed.resolved.provider_model,
            "provider_model_ref": routed.resolved.provider_model_ref,
            "gateway_model": routed.request.model,
            "thinking_enabled": routed.resolved.thinking_enabled,
        }
        if wire_api == "responses":
            route_trace["wire_api"] = "responses"
        trace_event(**route_trace)

        request_id = f"req_{uuid.uuid4().hex[:12]}"
        trace_event(
            stage="ingress",
            event=(
                "api.responses.request.received"
                if wire_api == "responses"
                else "api.request.received"
            ),
            source="api",
            message_count=len(routed.request.messages),
            snapshot=api_messages_request_snapshot(routed.request),
            request_id=request_id,
        )

        if self._settings.log_raw_api_payloads:
            logger.debug(f"{raw_log_label} [{{}}]: {{}}", request_id, raw_log_payload)

        input_tokens = self._token_counter(
            routed.request.messages,
            routed.request.system,
            routed.request.tools,
        )
        if self._quota_tracker is not None:
            self._quota_tracker.record_request(
                routed.resolved.provider_id,
                input_tokens=input_tokens,
            )
        return traced_async_stream(
            provider.stream_response(
                routed.request,
                input_tokens=input_tokens,
                request_id=request_id,
                thinking_enabled=routed.resolved.thinking_enabled,
            ),
            stage="egress",
            source="api",
            complete_event=(
                "api.responses.stream_completed"
                if wire_api == "responses"
                else "api.response.stream_completed"
            ),
            interrupted_event=(
                "api.responses.stream_interrupted"
                if wire_api == "responses"
                else "api.response.stream_interrupted"
            ),
            chunk_event=None,
            extra={
                "request_id": request_id,
                "provider_id": routed.resolved.provider_id,
                "gateway_model": routed.request.model,
            },
        )
