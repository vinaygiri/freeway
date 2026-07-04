from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from core.anthropic.streaming import format_sse_event


class FakeProvider:
    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self.preflight_stream = MagicMock()
        self.requests: list[Any] = []
        self.stream_kwargs: list[dict[str, Any]] = []

    async def stream_response(self, request_data, **_kwargs):
        self.requests.append(request_data)
        self.stream_kwargs.append(_kwargs)
        for chunk in self.chunks:
            yield chunk


@pytest.fixture
def chat_client():
    provider = FakeProvider(_anthropic_text_stream("Hello from provider"))
    app = create_app(lifespan_enabled=False)
    with (
        patch("api.dependencies.resolve_provider", return_value=provider),
        TestClient(app) as client,
    ):
        yield client, provider


def _parse_chat_sse(text: str) -> list[dict[str, Any]]:
    """Return parsed JSON payloads from a Chat Completions SSE body ([DONE] dropped)."""
    payloads: list[dict[str, Any]] = []
    for block in text.split("\n\n"):
        for line in block.splitlines():
            if not line.startswith("data:"):
                continue
            data = line.split(":", 1)[1].strip()
            if data and data != "[DONE]":
                payloads.append(json.loads(data))
    return payloads


def test_chat_probe_endpoints_return_204(
    chat_client: tuple[TestClient, FakeProvider],
) -> None:
    client, _provider = chat_client
    assert client.head("/v1/chat/completions").status_code == 204
    assert client.options("/v1/chat/completions").status_code == 204


def test_chat_stream_routes_through_provider(
    chat_client: tuple[TestClient, FakeProvider],
) -> None:
    client, provider = chat_client

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "nvidia_nim/test-model",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 32,
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert response.text.rstrip().endswith("data: [DONE]")
    chunks = _parse_chat_sse(response.text)
    assert chunks[0]["choices"][0]["delta"] == {"role": "assistant"}
    assert all(c["object"] == "chat.completion.chunk" for c in chunks)
    content = "".join(
        c["choices"][0]["delta"].get("content", "") for c in chunks if c["choices"]
    )
    assert content == "Hello from provider"
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"

    assert provider.preflight_stream.called
    routed = provider.requests[0]
    assert routed.model == "test-model"
    assert routed.messages[0].role == "user"
    assert routed.messages[0].content == "Hello"
    assert routed.max_tokens == 32


def test_chat_non_streaming_returns_completion_object(
    chat_client: tuple[TestClient, FakeProvider],
) -> None:
    client, _provider = chat_client

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "nvidia_nim/test-model",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["object"] == "chat.completion"
    choice = body["choices"][0]
    assert choice["message"]["role"] == "assistant"
    assert choice["message"]["content"] == "Hello from provider"
    assert choice["finish_reason"] == "stop"
    assert body["usage"] == {
        "prompt_tokens": 3,
        "completion_tokens": 4,
        "total_tokens": 7,
    }


def test_chat_defaults_to_non_streaming_when_stream_omitted(
    chat_client: tuple[TestClient, FakeProvider],
) -> None:
    client, _provider = chat_client
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "nvidia_nim/test-model",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )
    assert response.headers["content-type"].startswith("application/json")


def test_chat_hoists_system_message_and_merges_tool_results() -> None:
    provider = FakeProvider(_anthropic_text_stream("done"))
    app = create_app(lifespan_enabled=False)
    with (
        patch("api.dependencies.resolve_provider", return_value=provider),
        TestClient(app) as client,
    ):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "nvidia_nim/test-model",
                "messages": [
                    {"role": "system", "content": "Be terse."},
                    {"role": "user", "content": "hi"},
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "echo",
                                    "arguments": '{"value":"x"}',
                                },
                            }
                        ],
                    },
                    {"role": "tool", "tool_call_id": "call_1", "content": "ok"},
                ],
            },
        )

    assert response.status_code == 200
    routed = provider.requests[0]
    assert routed.system == "Be terse."
    assert routed.messages[0].role == "user"
    assert routed.messages[0].content == "hi"
    assert routed.messages[1].role == "assistant"
    assert routed.messages[1].content[0].type == "tool_use"
    assert routed.messages[1].content[0].name == "echo"
    assert routed.messages[2].role == "user"
    assert routed.messages[2].content[0].type == "tool_result"
    assert routed.messages[2].content[0].tool_use_id == "call_1"


def test_chat_stream_emits_tool_call_deltas() -> None:
    provider = FakeProvider(_anthropic_tool_stream())
    app = create_app(lifespan_enabled=False)
    with (
        patch("api.dependencies.resolve_provider", return_value=provider),
        TestClient(app) as client,
    ):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "nvidia_nim/test-model",
                "messages": [{"role": "user", "content": "use echo"}],
                "stream": True,
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "echo",
                            "parameters": {"type": "object", "properties": {}},
                        },
                    }
                ],
            },
        )

    assert response.status_code == 200
    chunks = _parse_chat_sse(response.text)
    tool_deltas = [
        c["choices"][0]["delta"]["tool_calls"][0]
        for c in chunks
        if c["choices"] and c["choices"][0]["delta"].get("tool_calls")
    ]
    assert tool_deltas[0]["id"] == "toolu_1"
    assert tool_deltas[0]["function"]["name"] == "echo"
    arguments = "".join(d["function"].get("arguments", "") for d in tool_deltas)
    assert arguments == '{"value":"FCC"}'
    assert chunks[-1]["choices"][0]["finish_reason"] == "tool_calls"
    routed = provider.requests[0]
    assert [tool.name for tool in routed.tools] == ["echo"]


def test_chat_non_streaming_tool_call_aggregates_arguments() -> None:
    provider = FakeProvider(_anthropic_tool_stream())
    app = create_app(lifespan_enabled=False)
    with (
        patch("api.dependencies.resolve_provider", return_value=provider),
        TestClient(app) as client,
    ):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "nvidia_nim/test-model",
                "messages": [{"role": "user", "content": "use echo"}],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "echo",
                            "parameters": {"type": "object", "properties": {}},
                        },
                    }
                ],
            },
        )

    assert response.status_code == 200
    message = response.json()["choices"][0]["message"]
    assert message["content"] is None
    call = message["tool_calls"][0]
    assert call["id"] == "toolu_1"
    assert call["function"]["name"] == "echo"
    assert call["function"]["arguments"] == '{"value":"FCC"}'
    assert response.json()["choices"][0]["finish_reason"] == "tool_calls"


def test_chat_stream_include_usage_emits_usage_chunk() -> None:
    provider = FakeProvider(_anthropic_text_stream("hi"))
    app = create_app(lifespan_enabled=False)
    with (
        patch("api.dependencies.resolve_provider", return_value=provider),
        TestClient(app) as client,
    ):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "nvidia_nim/test-model",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
                "stream_options": {"include_usage": True},
            },
        )

    chunks = _parse_chat_sse(response.text)
    usage_chunks = [c for c in chunks if c.get("usage")]
    assert usage_chunks[-1]["usage"] == {
        "prompt_tokens": 3,
        "completion_tokens": 4,
        "total_tokens": 7,
    }
    assert usage_chunks[-1]["choices"] == []


def test_chat_invalid_message_returns_openai_error(
    chat_client: tuple[TestClient, FakeProvider],
) -> None:
    client, provider = chat_client
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "nvidia_nim/test-model",
            "messages": [{"role": "banana", "content": "hi"}],
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["type"] == "invalid_request_error"
    assert provider.requests == []


def test_chat_non_streaming_provider_error_returns_502() -> None:
    provider = FakeProvider(
        [
            format_sse_event("message_start", {"type": "message_start", "message": {}}),
            format_sse_event(
                "error",
                {
                    "type": "error",
                    "error": {"type": "api_error", "message": "provider failed"},
                },
            ),
        ]
    )
    app = create_app(lifespan_enabled=False)
    with (
        patch("api.dependencies.resolve_provider", return_value=provider),
        TestClient(app) as client,
    ):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "nvidia_nim/test-model",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

    assert response.status_code == 502
    assert response.json()["error"]["message"] == "provider failed"


def _anthropic_text_stream(text: str) -> list[str]:
    return [
        format_sse_event("message_start", {"type": "message_start", "message": {}}),
        format_sse_event(
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        ),
        format_sse_event(
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": text},
            },
        ),
        format_sse_event(
            "content_block_stop",
            {"type": "content_block_stop", "index": 0},
        ),
        format_sse_event(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"input_tokens": 3, "output_tokens": 4},
            },
        ),
        format_sse_event("message_stop", {"type": "message_stop"}),
    ]


def _anthropic_tool_stream(
    tool_name: str = "echo", partial_json: str = '{"value":"FCC"}'
) -> list[str]:
    return [
        format_sse_event("message_start", {"type": "message_start", "message": {}}),
        format_sse_event(
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": tool_name,
                    "input": {},
                },
            },
        ),
        format_sse_event(
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": partial_json},
            },
        ),
        format_sse_event(
            "content_block_stop",
            {"type": "content_block_stop", "index": 0},
        ),
        format_sse_event(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "tool_use", "stop_sequence": None},
                "usage": {"input_tokens": 3, "output_tokens": 4},
            },
        ),
        format_sse_event("message_stop", {"type": "message_stop"}),
    ]
