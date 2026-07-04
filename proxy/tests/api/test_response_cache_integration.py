"""Integration tests: MessagesHandler served through the response cache."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.responses import StreamingResponse

from api.handlers import MessagesHandler
from api.models.anthropic import Message, MessagesRequest, Tool
from config.settings import Settings
from core.response_cache import ResponseCache
from providers.base import BaseProvider, ProviderConfig


class CountingProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(ProviderConfig(api_key="test"))
        self.calls = 0

    def preflight_stream(
        self, request: Any, *, thinking_enabled: bool | None = None
    ) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    async def list_model_ids(self) -> frozenset[str]:
        return frozenset({"test-model"})

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        self.calls += 1
        yield 'event: message_start\ndata: {"type":"message_start"}\n\n'
        yield 'event: message_stop\ndata: {"type":"message_stop"}\n\n'


async def _body(response: object) -> str:
    assert isinstance(response, StreamingResponse)
    parts = [
        chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
        async for chunk in response.body_iterator
    ]
    return "".join(parts)


def _request(**overrides: Any) -> MessagesRequest:
    base: dict[str, Any] = {
        "model": "nvidia_nim/test-model",
        "max_tokens": 100,
        "messages": [Message(role="user", content="hi")],
        "temperature": 0,
    }
    base.update(overrides)
    return MessagesRequest(**base)


@pytest.mark.asyncio
async def test_identical_cacheable_request_served_from_cache() -> None:
    provider = CountingProvider()
    cache = ResponseCache()
    handler = MessagesHandler(
        Settings(), provider_getter=lambda _: provider, response_cache=cache
    )

    first = await _body(handler.create(_request()))
    assert provider.calls == 1
    assert "message_stop" in first

    second = await _body(handler.create(_request()))
    # Replayed from cache — provider not hit a second time.
    assert provider.calls == 1
    assert second == first

    snap = cache.snapshot()
    assert snap["entries"] == 1
    assert snap["hits"] == 1


@pytest.mark.asyncio
async def test_non_cacheable_request_bypasses_cache() -> None:
    provider = CountingProvider()
    cache = ResponseCache()
    handler = MessagesHandler(
        Settings(), provider_getter=lambda _: provider, response_cache=cache
    )

    # No explicit temperature=0 -> not cacheable.
    await _body(handler.create(_request(temperature=None)))
    await _body(handler.create(_request(temperature=None)))

    assert provider.calls == 2
    assert cache.snapshot()["entries"] == 0


@pytest.mark.asyncio
async def test_tool_request_bypasses_cache() -> None:
    provider = CountingProvider()
    cache = ResponseCache()
    handler = MessagesHandler(
        Settings(), provider_getter=lambda _: provider, response_cache=cache
    )
    tool = Tool(name="get_weather", input_schema={"type": "object"})

    await _body(handler.create(_request(tools=[tool])))
    await _body(handler.create(_request(tools=[tool])))

    assert provider.calls == 2
    assert cache.snapshot()["entries"] == 0


@pytest.mark.asyncio
async def test_no_cache_configured_still_works() -> None:
    provider = CountingProvider()
    handler = MessagesHandler(Settings(), provider_getter=lambda _: provider)

    await _body(handler.create(_request()))
    await _body(handler.create(_request()))

    assert provider.calls == 2


@pytest.mark.asyncio
async def test_different_requests_cache_independently() -> None:
    provider = CountingProvider()
    cache = ResponseCache()
    handler = MessagesHandler(
        Settings(), provider_getter=lambda _: provider, response_cache=cache
    )

    await _body(handler.create(_request(messages=[Message(role="user", content="a")])))
    await _body(handler.create(_request(messages=[Message(role="user", content="b")])))
    assert provider.calls == 2
    assert cache.snapshot()["entries"] == 2

    # Repeat the first -> served from cache.
    await _body(handler.create(_request(messages=[Message(role="user", content="a")])))
    assert provider.calls == 2
