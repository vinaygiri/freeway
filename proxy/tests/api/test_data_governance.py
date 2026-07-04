from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import create_app


def test_admin_policy_endpoint_reports_inactive_by_default():
    app = create_app(lifespan_enabled=False)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        body = client.get("/admin/api/policy").json()
    assert body["active"] is False
    assert "nvidia_nim" in body["providers"]
    # Default (no policy) -> everything allowed.
    assert body["providers"]["nvidia_nim"]["allowed"] is True
    assert body["providers"]["ollama"]["reason"] is None


def test_admin_policy_requires_loopback():
    app = create_app(lifespan_enabled=False)
    with TestClient(app, client=("203.0.113.10", 50000)) as remote:
        assert remote.get("/admin/api/policy").status_code == 403
