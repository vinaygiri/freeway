from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import create_app
from core.anthropic.streaming import format_sse_event
from core.recent_requests import RecentRequestStore
from providers.base import BaseProvider


class _FakeProvider(BaseProvider):
    def __init__(self) -> None:
        pass

    async def cleanup(self) -> None:
        return None

    async def list_model_ids(self) -> frozenset[str]:
        return frozenset()

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        yield format_sse_event(
            "message_start", {"type": "message_start", "message": {}}
        )
        yield format_sse_event(
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        )
        yield format_sse_event(
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "hi"},
            },
        )
        yield format_sse_event(
            "content_block_stop", {"type": "content_block_stop", "index": 0}
        )
        yield format_sse_event(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
        )
        yield format_sse_event("message_stop", {"type": "message_stop"})


def test_chat_request_recorded_and_visible_in_admin():
    app = create_app(lifespan_enabled=False)
    app.state.recent_request_store = RecentRequestStore()
    with (
        patch("api.dependencies.resolve_provider", return_value=_FakeProvider()),
        TestClient(app, client=("127.0.0.1", 50000)) as client,
    ):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "nvidia_nim/test-model",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        assert response.status_code == 200
        admin = client.get("/admin/api/requests")

    assert admin.status_code == 200
    body = admin.json()
    assert body["enabled"] is True
    record = body["requests"][0]
    assert record["provider_id"] == "nvidia_nim"
    assert record["provider_model"] == "test-model"
    assert record["outcome"] == "routed"
    assert record["was_fallback"] is False


def test_admin_requests_requires_loopback():
    app = create_app(lifespan_enabled=False)
    app.state.recent_request_store = RecentRequestStore()
    with TestClient(app, client=("203.0.113.10", 50000)) as remote:
        assert remote.get("/admin/api/requests").status_code == 403


def test_admin_requests_empty_without_store():
    app = create_app(lifespan_enabled=False)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        body = client.get("/admin/api/requests").json()
    assert body["requests"] == []
