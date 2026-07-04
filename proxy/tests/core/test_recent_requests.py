from __future__ import annotations

from core.recent_requests import RecentRequest, RecentRequestStore


def _rec(request_id: str, outcome: str = "routed") -> RecentRequest:
    return RecentRequest(
        at=1.0,
        request_id=request_id,
        gateway_model="claude-sonnet-4",
        provider_id="groq",
        provider_model="llama-3.3",
        input_tokens=5,
        was_fallback=False,
        candidates_tried=1,
        downgrade_reason=None,
        outcome=outcome,
    )


def test_snapshot_is_newest_first():
    store = RecentRequestStore()
    store.record(_rec("a"))
    store.record(_rec("b"))
    snapshot = store.snapshot()
    assert [r["request_id"] for r in snapshot] == ["b", "a"]
    assert snapshot[0]["provider_id"] == "groq"
    assert snapshot[0]["outcome"] == "routed"


def test_bounded_window_drops_oldest():
    store = RecentRequestStore(window=2)
    for request_id in ("a", "b", "c"):
        store.record(_rec(request_id))
    assert [r["request_id"] for r in store.snapshot()] == ["c", "b"]


def test_empty_snapshot():
    assert RecentRequestStore().snapshot() == []
