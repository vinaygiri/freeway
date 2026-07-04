from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.health_probe import HealthProbeService
from config.settings import Settings
from core.health import HealthStore, Sample
from providers.base import BaseProvider
from providers.exceptions import AuthenticationError


def _app_with_store(store: HealthStore | None):
    app = create_app(lifespan_enabled=False)
    if store is not None:
        app.state.health_store = store
    return app


def test_health_stats_reports_disabled_without_store():
    with TestClient(_app_with_store(None)) as client:
        response = client.get("/v1/health/stats")
    assert response.status_code == 200
    assert response.json() == {"enabled": False, "targets": {}}


def test_health_stats_returns_target_summaries():
    store = HealthStore()
    store.record("nvidia_nim", Sample(code="200", latency_ms=200))
    store.record("nvidia_nim", Sample(code="200", latency_ms=220))
    with TestClient(_app_with_store(store)) as client:
        response = client.get("/v1/health/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["targets"]["nvidia_nim"]["uptime"] == 100
    assert body["targets"]["nvidia_nim"]["stability_score"] > 0


def test_health_stats_probe_endpoints_return_204():
    with TestClient(_app_with_store(None)) as client:
        assert client.head("/v1/health/stats").status_code == 204
        assert client.options("/v1/health/stats").status_code == 204


def test_admin_health_requires_loopback():
    store = HealthStore()
    store.record("groq", Sample(code="200", latency_ms=90))
    app = _app_with_store(store)

    with TestClient(app, client=("203.0.113.10", 50000)) as remote:
        assert remote.get("/admin/api/health").status_code == 403

    with TestClient(app, client=("127.0.0.1", 50000)) as local:
        response = local.get("/admin/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["interval_seconds"] == 60
    assert body["targets"]["groq"]["verdict"] == "Perfect"


class _FakeProvider(BaseProvider):
    def __init__(self, *, raises: Exception | None = None) -> None:
        self._raises = raises

    async def cleanup(self) -> None:
        return None

    async def list_model_ids(self) -> frozenset[str]:
        if self._raises is not None:
            raise self._raises
        return frozenset({"model-a"})

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        if False:
            yield ""


@pytest.mark.asyncio
async def test_probe_once_records_success_auth_and_error_samples():
    store = HealthStore()
    providers = {
        "ok": _FakeProvider(),
        "auth": _FakeProvider(raises=AuthenticationError("bad key")),
        "broken": _FakeProvider(raises=RuntimeError("boom")),
    }
    service = HealthProbeService(
        Settings(),
        providers.__getitem__,
        store,
        interval_s=60,
    )

    with patch(
        "api.health_probe.model_list_provider_ids_for_settings",
        return_value=("ok", "auth", "broken"),
    ):
        await service.probe_once()

    ok = store.summary("ok")
    auth = store.summary("auth")
    broken = store.summary("broken")
    assert ok is not None and ok["last_code"] == "200"
    ok_score = ok["stability_score"]
    assert isinstance(ok_score, int) and ok_score >= 0
    assert auth is not None and auth["last_code"] == "401"
    assert broken is not None
    assert broken["last_code"] == "ERR"
    assert broken["stability_score"] == -1
