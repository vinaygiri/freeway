from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import create_app
from api.quota_governor import QuotaGovernor
from config.provider_quota import ProviderQuotaLimit
from core.anthropic.streaming import format_sse_event
from core.quota import QuotaTracker
from providers.base import BaseProvider

_LIMITS = {
    "groq": ProviderQuotaLimit(provider_id="groq", rpm=30, requests_per_day=100),
}


# -- governor ---------------------------------------------------------------
def test_assess_ok_below_threshold():
    tracker = QuotaTracker()
    governor = QuotaGovernor(tracker, _LIMITS)
    for _ in range(5):
        tracker.record_request("groq")
    assessment: Any = governor.assess("groq")
    assert assessment["status"] == "ok"
    assert assessment["avoid"] is False
    assert assessment["dimensions"]["rpm"]["used"] == 5
    assert assessment["dimensions"]["rpm"]["remaining"] == 25


def test_assess_warning_then_exhausted_and_avoid():
    tracker = QuotaTracker()
    governor = QuotaGovernor(tracker, _LIMITS)
    for _ in range(27):  # 27/30 rpm = 0.9 -> warning
        tracker.record_request("groq")
    assert governor.assess("groq")["status"] == "warning"
    for _ in range(5):  # 32/30 -> exhausted
        tracker.record_request("groq")
    exhausted = governor.assess("groq")
    assert exhausted["status"] == "exhausted"
    assert exhausted["avoid"] is True
    assert governor.should_avoid("groq") is True


def test_assess_unknown_provider():
    governor = QuotaGovernor(QuotaTracker(), _LIMITS)
    assessment = governor.assess("mystery")
    assert assessment["status"] == "unknown"
    assert assessment["utilization"] is None
    assert assessment["avoid"] is False


def test_seconds_to_exhaustion_projects_from_minute_rate():
    tracker = QuotaTracker()
    governor = QuotaGovernor(
        tracker,
        {"groq": ProviderQuotaLimit(provider_id="groq", requests_per_day=100)},
    )
    for _ in range(10):  # 10 req in the last minute -> ~0.1667 req/s
        tracker.record_request("groq")
    ttx = governor.assess("groq")["seconds_to_exhaustion"]
    assert isinstance(ttx, float)
    assert 500 < ttx < 560  # remaining 90 / (10/60) = 540s


def test_snapshot_unions_tracker_and_limits():
    tracker = QuotaTracker()
    governor = QuotaGovernor(tracker, _LIMITS)
    tracker.record_request("nvidia_nim")  # tracked but not in _LIMITS
    snapshot = governor.snapshot()
    assert "groq" in snapshot  # from limits
    assert "nvidia_nim" in snapshot  # from tracker
    assert snapshot["nvidia_nim"]["status"] == "unknown"


# -- endpoints --------------------------------------------------------------
def test_quota_stats_disabled_without_governor():
    with TestClient(create_app(lifespan_enabled=False)) as client:
        response = client.get("/v1/quota/stats")
    assert response.status_code == 200
    assert response.json() == {"enabled": False, "providers": {}}


def test_quota_stats_returns_snapshot():
    app = create_app(lifespan_enabled=False)
    tracker = QuotaTracker()
    for _ in range(3):
        tracker.record_request("groq", input_tokens=5)
    app.state.quota_tracker = tracker
    app.state.quota_governor = QuotaGovernor(tracker)  # real catalog: groq rpm=30
    with TestClient(app) as client:
        response = client.get("/v1/quota/stats")
    body = response.json()
    assert body["enabled"] is True
    assert body["providers"]["groq"]["dimensions"]["rpm"]["used"] == 3


def test_quota_stats_probe_endpoints_return_204():
    with TestClient(create_app(lifespan_enabled=False)) as client:
        assert client.head("/v1/quota/stats").status_code == 204
        assert client.options("/v1/quota/stats").status_code == 204


def test_admin_quota_requires_loopback():
    app = create_app(lifespan_enabled=False)
    tracker = QuotaTracker()
    tracker.record_request("groq")
    app.state.quota_tracker = tracker
    app.state.quota_governor = QuotaGovernor(tracker)

    with TestClient(app, client=("203.0.113.10", 50000)) as remote:
        assert remote.get("/admin/api/quota").status_code == 403

    with TestClient(app, client=("127.0.0.1", 50000)) as local:
        response = local.get("/admin/api/quota")
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert "groq" in response.json()["providers"]


# -- integration: recording through the real request path -------------------
class _FakeProvider(BaseProvider):
    def __init__(self) -> None:
        pass

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


def test_chat_completion_records_quota_consumption():
    app = create_app(lifespan_enabled=False)
    tracker = QuotaTracker()
    app.state.quota_tracker = tracker
    with (
        patch("api.dependencies.resolve_provider", return_value=_FakeProvider()),
        TestClient(app) as client,
    ):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "nvidia_nim/test-model",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert response.status_code == 200
    usage = tracker.usage("nvidia_nim")
    assert usage["requests_last_minute"] == 1
    assert usage["input_tokens_last_day"] >= 1
