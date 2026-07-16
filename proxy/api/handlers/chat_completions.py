"""OpenAI Chat Completions API product flow for OpenAI-compatible tools."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.responses import JSONResponse

from api.model_router import ModelRouter
from api.models.anthropic import MessagesRequest
from api.models.openai_chat_completions import ChatCompletionsRequest
from api.provider_execution import ProviderExecutionService
from api.request_errors import (
    http_status_for_unexpected_api_exception,
    log_unexpected_api_exception,
    require_non_empty_messages,
)
from api.response_streams import openai_responses_sse_streaming_response
from api.router_policy import RoutingPolicy
from config.settings import Settings
from core.anthropic import get_user_facing_error_message
from core.openai_chat_completions import OpenAIChatCompletionsAdapter
from core.quota import QuotaTracker
from providers.base import BaseProvider
from providers.exceptions import InvalidRequestError, ProviderError

ProviderGetter = Callable[[str], BaseProvider]

# Upstream stream failures surface after a provider was resolved; report them as
# a bad-gateway rather than a client (4xx) or generic server (500) error.
_UPSTREAM_STREAM_ERROR_STATUS = 502


class ChatCompletionsHandler:
    """Handle streaming and non-streaming OpenAI Chat Completions requests."""

    def __init__(
        self,
        settings: Settings,
        provider_getter: ProviderGetter,
        *,
        model_router: ModelRouter | None = None,
        chat_adapter: OpenAIChatCompletionsAdapter | None = None,
        provider_execution: ProviderExecutionService | None = None,
        quota_tracker: QuotaTracker | None = None,
        routing_policy: RoutingPolicy | None = None,
    ) -> None:
        self._settings = settings
        self._model_router = model_router or ModelRouter(settings)
        self._chat_adapter = chat_adapter or OpenAIChatCompletionsAdapter()
        self._provider_execution = provider_execution or ProviderExecutionService(
            settings,
            provider_getter,
            quota_tracker=quota_tracker,
            routing_policy=routing_policy,
        )

    async def create(self, request_data: ChatCompletionsRequest) -> object:
        """Create a streaming or non-streaming Chat Completions response."""
        request_payload = request_data.model_dump(mode="json", exclude_none=True)
        streaming = request_data.stream is True
        try:
            anthropic_payload = self._chat_adapter.to_anthropic_payload(request_payload)
            chat_request = MessagesRequest(**anthropic_payload)
            require_non_empty_messages(chat_request.messages)
            routed = self._model_router.resolve_messages_request(chat_request)

            streamed = await self._provider_execution.stream_with_failover(
                routed,
                self._model_router.resolve_fallback_candidates(),
                wire_api="chat_completions",
                raw_log_label="FULL_CHAT_COMPLETIONS_PAYLOAD",
                raw_log_payload=request_payload,
            )
            if streaming:
                return openai_responses_sse_streaming_response(
                    self._chat_adapter.iter_sse_from_anthropic(
                        streamed,
                        request_payload,
                    ),
                    headers=self._chat_adapter.sse_headers,
                )
            completion = await self._chat_adapter.aggregate_from_anthropic(
                streamed,
                request_payload,
            )
            return JSONResponse(content=completion)
        except OpenAIChatCompletionsAdapter.ConversionError as exc:
            invalid_request = InvalidRequestError(str(exc))
            return JSONResponse(
                status_code=invalid_request.status_code,
                content=self._chat_adapter.error_payload(
                    message=invalid_request.message,
                    error_type=invalid_request.error_type,
                ),
            )
        except OpenAIChatCompletionsAdapter.StreamError as exc:
            return JSONResponse(
                status_code=_UPSTREAM_STREAM_ERROR_STATUS,
                content=exc.payload,
            )
        except ProviderError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content=self._chat_adapter.error_payload(
                    message=exc.message,
                    error_type=exc.error_type,
                ),
            )
        except Exception as exc:
            log_unexpected_api_exception(
                self._settings,
                exc,
                context="CREATE_CHAT_COMPLETION_ERROR",
            )
            return JSONResponse(
                status_code=http_status_for_unexpected_api_exception(exc),
                content=self._chat_adapter.error_payload(
                    message=get_user_facing_error_message(exc),
                    error_type="api_error",
                ),
            )
