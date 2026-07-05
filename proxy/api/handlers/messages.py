"""Claude Messages API product flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from loguru import logger

from api.auto_fit import (
    parse_keep_tools,
    trim_messages_to_budget,
    trim_tools_to_budget,
)
from api.detection import is_safety_classifier_request
from api.model_router import ModelRouter, RoutedMessagesRequest
from api.models.anthropic import MessagesRequest
from api.optimization_handlers import try_optimizations
from api.provider_execution import ProviderExecutionService, TokenCounter
from api.request_errors import require_non_empty_messages, unexpected_http_exception
from api.response_cache_keys import cache_key, is_cacheable
from api.response_streams import anthropic_sse_streaming_response
from api.router_policy import RoutingPolicy
from api.tool_filter import filter_tools, parse_drop_tools
from api.web_tools.egress import WebFetchEgressPolicy, web_fetch_allowed_scheme_set
from api.web_tools.request import (
    is_web_server_tool_request,
    openai_chat_upstream_server_tool_error,
)
from api.web_tools.streaming import stream_web_server_tool_response
from config.model_quality import context_tokens_for
from config.provider_catalog import PROVIDER_CATALOG
from config.settings import Settings
from core.anthropic import get_token_count
from core.quota import QuotaTracker
from core.response_cache import ResponseCache, capture_and_cache, replay
from core.trace import trace_event
from providers.base import BaseProvider
from providers.exceptions import InvalidRequestError, ProviderError

ProviderGetter = Callable[[str], BaseProvider]
MessageIntercept = Callable[[RoutedMessagesRequest], object | None]

_OPENAI_CHAT_UPSTREAM_IDS = frozenset(
    provider_id
    for provider_id, descriptor in PROVIDER_CATALOG.items()
    if descriptor.transport_type == "openai_chat"
)


class MessagesHandler:
    """Handle Anthropic-compatible Messages requests."""

    def __init__(
        self,
        settings: Settings,
        provider_getter: ProviderGetter,
        *,
        model_router: ModelRouter | None = None,
        token_counter: TokenCounter = get_token_count,
        provider_execution: ProviderExecutionService | None = None,
        quota_tracker: QuotaTracker | None = None,
        routing_policy: RoutingPolicy | None = None,
        response_cache: ResponseCache | None = None,
    ) -> None:
        self._settings = settings
        self._model_router = model_router or ModelRouter(settings)
        self._token_counter = token_counter
        self._response_cache = response_cache
        self._provider_execution = provider_execution or ProviderExecutionService(
            settings,
            provider_getter,
            token_counter=token_counter,
            quota_tracker=quota_tracker,
            routing_policy=routing_policy,
        )
        self._message_intercepts: tuple[MessageIntercept, ...] = (
            self._intercept_web_server_tool,
            self._intercept_local_optimization,
        )

    def create(self, request_data: MessagesRequest) -> object:
        """Create an Anthropic-compatible message response."""
        try:
            require_non_empty_messages(request_data.messages)
            routed = self._model_router.resolve_messages_request(request_data)
            routed = self._apply_tool_filter(routed)
            routed = self._apply_auto_fit(routed)
            routed = self._apply_message_routing_policies(routed)
            self._reject_unsupported_server_tools(routed)

            intercepted = self._run_message_intercepts(routed)
            if intercepted is not None:
                return intercepted

            # Exact-match response cache: serve identical safe requests without
            # touching a provider; capture the miss only on clean completion.
            cache_hit_key = self._cacheable_key(routed)
            if cache_hit_key is not None and self._response_cache is not None:
                cached = self._response_cache.get(cache_hit_key)
                if cached is not None:
                    return anthropic_sse_streaming_response(replay(cached))

            logger.debug("No optimization matched, routing to provider")
            stream = self._provider_execution.stream_with_failover(
                routed,
                self._model_router.resolve_fallback_candidates(),
                wire_api="messages",
                raw_log_label="FULL_PAYLOAD",
                raw_log_payload=routed.request.model_dump(),
            )
            if cache_hit_key is not None and self._response_cache is not None:
                stream = capture_and_cache(stream, self._response_cache, cache_hit_key)
            return anthropic_sse_streaming_response(stream)
        except ProviderError:
            raise
        except Exception as exc:
            raise unexpected_http_exception(
                self._settings, exc, context="CREATE_MESSAGE_ERROR"
            ) from exc

    def _apply_tool_filter(
        self, routed: RoutedMessagesRequest
    ) -> RoutedMessagesRequest:
        """Strip DROP_TOOLS-matched tool schemas before the request goes upstream."""
        patterns = parse_drop_tools(self._settings.drop_tools)
        original = routed.request.tools
        if not patterns or not original:
            return routed
        filtered = filter_tools(original, patterns)
        dropped = len(original) - (len(filtered) if filtered else 0)
        if dropped == 0:
            return routed
        logger.debug(
            "DROP_TOOLS removed {} of {} tools before forwarding",
            dropped,
            len(original),
        )
        new_request = routed.request.model_copy(update={"tools": filtered})
        return RoutedMessagesRequest(request=new_request, resolved=routed.resolved)

    def _resolve_fit_budget(self, routed: RoutedMessagesRequest) -> int:
        """Token budget for auto-fit: explicit ``AUTO_FIT_MAX_TOKENS`` when > 0, or
        (default) auto-sized to 90% of the routed model's advertised context so a
        fresh install protects every provider without manual tuning. Negative
        disables it; unknown context means no trimming (so behavior is unchanged)."""
        configured = self._settings.auto_fit_max_tokens
        if configured > 0:
            return configured
        if configured < 0:
            return 0
        context = context_tokens_for(routed.resolved.provider_model)
        return int(context * 0.9) if context else 0

    def _apply_auto_fit(self, routed: RoutedMessagesRequest) -> RoutedMessagesRequest:
        """Fit an over-budget request to ``AUTO_FIT_MAX_TOKENS``.

        Two stages: drop the largest non-essential tool schemas first (cheap, keeps
        conversation intact), then — if the request is *still* over budget because
        the conversation itself grew too large — drop the oldest whole turns as a
        last-resort backstop so it can never exceed the provider's limit.
        """
        max_tokens = self._resolve_fit_budget(routed)
        if max_tokens <= 0:
            return routed
        request = routed.request
        updates: dict[str, Any] = {}

        kept_tools = request.tools
        if request.tools:
            keep_names = parse_keep_tools(self._settings.auto_fit_keep_tools)
            kept_tools = trim_tools_to_budget(
                messages=request.messages,
                system=request.system,
                tools=request.tools,
                max_tokens=max_tokens,
                keep_names=keep_names,
                count_tokens=self._token_counter,
            )
            if len(kept_tools or []) != len(request.tools):
                updates["tools"] = kept_tools
                logger.debug(
                    "AUTO_FIT dropped {} of {} tools to fit {} tokens",
                    len(request.tools) - len(kept_tools or []),
                    len(request.tools),
                    max_tokens,
                )

        kept_messages = trim_messages_to_budget(
            messages=request.messages,
            system=request.system,
            tools=kept_tools,
            max_tokens=max_tokens,
            count_tokens=self._token_counter,
        )
        if len(kept_messages) != len(request.messages):
            updates["messages"] = kept_messages
            logger.debug(
                "AUTO_FIT dropped {} of {} oldest messages to fit {} tokens (now ~{})",
                len(request.messages) - len(kept_messages),
                len(request.messages),
                max_tokens,
                self._token_counter(kept_messages, request.system, kept_tools),
            )

        if not updates:
            return routed
        new_request = request.model_copy(update=updates)
        return RoutedMessagesRequest(request=new_request, resolved=routed.resolved)

    def _cacheable_key(self, routed: RoutedMessagesRequest) -> str | None:
        """Return the response-cache key when caching applies, else ``None``."""
        if self._response_cache is None or not is_cacheable(routed.request):
            return None
        return cache_key(routed.request)

    def _reject_unsupported_server_tools(self, routed: RoutedMessagesRequest) -> None:
        if routed.resolved.provider_id not in _OPENAI_CHAT_UPSTREAM_IDS:
            return
        tool_err = openai_chat_upstream_server_tool_error(
            routed.request,
            web_tools_enabled=self._settings.enable_web_server_tools,
        )
        if tool_err is not None:
            raise InvalidRequestError(tool_err)

    def _apply_message_routing_policies(
        self, routed: RoutedMessagesRequest
    ) -> RoutedMessagesRequest:
        if not is_safety_classifier_request(routed.request):
            return routed
        changed = routed.resolved.thinking_enabled
        trace_event(
            stage="routing",
            event="api.optimization.safety_classifier_no_thinking",
            source="api",
            model=routed.request.model,
            changed=changed,
        )
        if not changed:
            return routed
        return RoutedMessagesRequest(
            request=routed.request,
            resolved=replace(routed.resolved, thinking_enabled=False),
        )

    def _run_message_intercepts(self, routed: RoutedMessagesRequest) -> object | None:
        for intercept in self._message_intercepts:
            result = intercept(routed)
            if result is not None:
                return result
        return None

    def _intercept_web_server_tool(
        self, routed: RoutedMessagesRequest
    ) -> object | None:
        if not self._settings.enable_web_server_tools:
            return None
        if not is_web_server_tool_request(routed.request):
            return None

        input_tokens = self._token_counter(
            routed.request.messages, routed.request.system, routed.request.tools
        )
        trace_event(
            stage="routing",
            event="api.optimization.web_server_tool",
            source="api",
            model=routed.request.model,
        )
        egress = WebFetchEgressPolicy(
            allow_private_network_targets=self._settings.web_fetch_allow_private_networks,
            allowed_schemes=web_fetch_allowed_scheme_set(
                self._settings.web_fetch_allowed_schemes
            ),
        )
        return anthropic_sse_streaming_response(
            stream_web_server_tool_response(
                routed.request,
                input_tokens=input_tokens,
                web_fetch_egress=egress,
                verbose_client_errors=self._settings.log_api_error_tracebacks,
            ),
        )

    def _intercept_local_optimization(
        self, routed: RoutedMessagesRequest
    ) -> object | None:
        optimized = try_optimizations(routed.request, self._settings)
        if optimized is None:
            return None
        trace_event(
            stage="routing",
            event="api.optimization.short_circuit",
            source="api",
            model=routed.request.model,
        )
        return optimized
