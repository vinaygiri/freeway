from __future__ import annotations

from core.health.score import Sample
from core.health.store import HealthStore


def test_record_and_summary():
    store = HealthStore()
    store.record("nvidia_nim", Sample(code="200", latency_ms=120))
    store.record("nvidia_nim", Sample(code="200", latency_ms=140))

    summary = store.summary("nvidia_nim")
    assert summary is not None
    assert summary["sample_count"] == 2
    assert summary["avg_ms"] == 130
    assert summary["uptime"] == 100
    assert summary["verdict"] == "Perfect"


def test_summary_none_for_unknown_target():
    assert HealthStore().summary("missing") is None


def test_bounded_window_drops_oldest():
    store = HealthStore(window=3)
    for ms in (100, 200, 300, 400, 500):
        store.record("groq", Sample(code="200", latency_ms=ms))
    samples = store.samples("groq")
    assert [s.latency_ms for s in samples] == [300, 400, 500]


def test_snapshot_covers_all_targets():
    store = HealthStore()
    store.record("groq", Sample(code="200", latency_ms=100))
    store.record("cerebras", Sample(code="ERR"))
    snapshot = store.snapshot()
    assert set(snapshot) == {"groq", "cerebras"}
    assert snapshot["cerebras"]["stability_score"] == -1
