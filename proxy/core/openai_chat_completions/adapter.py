"""Facade for OpenAI Chat Completions protocol adaptation."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Mapping
from typing import Any, ClassVar

from .errors import (
    ChatCompletionsConversionError,
    ChatCompletionsStreamError,
    openai_error_payload,
)
from .input import convert_request_to_anthropic_payload
from .stream import (
    aggregate_chat_completion_from_anthropic,
    iter_chat_sse_from_anthropic,
)

_SSE_HEADERS: dict[str, str] = {
    "X-Accel-Buffering": "no",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}


class OpenAIChatCompletionsAdapter:
    """Convert between OpenAI Chat Completions and the proxy's Anthropic core path."""

    ConversionError: ClassVar[type[ChatCompletionsConversionError]] = (
        ChatCompletionsConversionError
    )
    StreamError: ClassVar[type[ChatCompletionsStreamError]] = ChatCompletionsStreamError
    sse_headers: ClassVar[dict[str, str]] = _SSE_HEADERS

    def to_anthropic_payload(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return convert_request_to_anthropic_payload(request)

    def iter_sse_from_anthropic(
        self,
        chunks: AsyncIterable[Any],
        request: Mapping[str, Any],
    ) -> AsyncIterator[str]:
        return iter_chat_sse_from_anthropic(chunks, request)

    async def aggregate_from_anthropic(
        self,
        chunks: AsyncIterable[Any],
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        return await aggregate_chat_completion_from_anthropic(chunks, request)

    def error_payload(self, *, message: str, error_type: str) -> dict[str, Any]:
        return openai_error_payload(message=message, error_type=error_type)
