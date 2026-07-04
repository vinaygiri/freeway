"""Tests for the /admin/api/cache stats endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import create_app
from core.response_cache import ResponseCache


def test_admin_cache_reports_stats_when_installed() -> None:
    app = create_app(lifespan_enabled=False)
    cache = ResponseCache()
    cache.put("k", ["chunk"])
    cache.get("k")
    cache.get("absent")
    app.state.response_cache = cache

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        body = client.get("/admin/api/cache").json()

    assert body["stats"] == {"entries": 1, "hits": 1, "misses": 1}
    assert "enabled" in body
    assert "window" in body
    assert "ttl_seconds" in body


def test_admin_cache_clear_empties_the_cache() -> None:
    app = create_app(lifespan_enabled=False)
    cache = ResponseCache()
    cache.put("k", ["chunk"])
    cache.get("k")
    app.state.response_cache = cache

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        body = client.post("/admin/api/cache/clear", json={}).json()

    assert body["cleared"] is True
    assert body["stats"] == {"entries": 0, "hits": 0, "misses": 0}
    assert cache.snapshot() == {"entries": 0, "hits": 0, "misses": 0}


def test_admin_models_include_quality_and_usability() -> None:
    app = create_app(lifespan_enabled=False)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        body = client.get("/admin/api/models").json()

    assert "favourites" in body
    provider = body["providers"][0]
    for key in ("usable", "usable_reason", "models"):
        assert key in provider
    # Every model row carries the quality-catalog fields (values may be null).
    for prov in body["providers"]:
        for model in prov["models"]:
            for key in ("tier", "swe_score", "context", "score_num", "is_favourite"):
                assert key in model


def test_admin_cache_empty_without_cache() -> None:
    app = create_app(lifespan_enabled=False)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        body = client.get("/admin/api/cache").json()
    assert body["stats"] == {}
    assert body["enabled"] is False


def test_admin_cache_requires_loopback() -> None:
    app = create_app(lifespan_enabled=False)
    app.state.response_cache = ResponseCache()
    with TestClient(app, client=("203.0.113.10", 50000)) as remote:
        assert remote.get("/admin/api/cache").status_code == 403
