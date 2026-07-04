"""Shared provider execution primitive for API product handlers."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi import HTTPException
from loguru import logger

from config.settings import Settings
from core.anthropic import get_token_count
from core.quota import QuotaTracker
from core.trace import api_messages_request_snapshot, trace_event, traced_async_stream
from providers.base import BaseProvider
from providers.exceptions import (
    APIError,
    AuthenticationError,
    ProviderError,
    ServiceUnavailableError,
)

from .model_router import ResolvedModel, RoutedMessagesRequest
from .router_policy import RoutingPolicy

_AUTH_HTTP_STATUSES = frozenset({401, 403})

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

    def stream_with_failover(
        self,
        primary: RoutedMessagesRequest,
        fallbacks: list[ResolvedModel],
        *,
        wire_api: str,
        raw_log_label: str,
        raw_log_payload: Any,
    ) -> AsyncIterator[str]:
        """Stream the first candidate that survives eager preflight, failing over.

        Candidates (primary + fallbacks) are ordered by the routing policy
        (skipping circuit-open / quota-exhausted / dead-health providers). Each
        attempt runs provider resolution + preflight eagerly; a failure there
        records a circuit failure and moves to the next candidate. Failures that
        occur mid-stream (after this returns) are out of scope for M4a.
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
        attempts = 0
        for resolved in candidates:
            if attempts >= policy.max_attempts:
                break
            if resolved.provider_id in blocked_providers:
                continue
            attempts += 1
            routed = self._routed_for(primary, resolved)
            try:
                iterator = self.stream(
                    routed,
                    wire_api=wire_api,
                    raw_log_label=raw_log_label,
                    raw_log_payload=raw_log_payload,
                )
            except ProviderError as exc:
                policy.record_failure(resolved)
                if isinstance(exc, AuthenticationError):
                    blocked_providers.add(resolved.provider_id)
                last_error = exc
                continue
            except HTTPException as exc:
                policy.record_failure(resolved)
                if exc.status_code in _AUTH_HTTP_STATUSES:
                    blocked_providers.add(resolved.provider_id)
                last_error = APIError(str(exc.detail), status_code=exc.status_code)
                continue
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
            return iterator
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
