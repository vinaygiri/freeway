"""Tests for per-model liveness probe classification and persistent storage."""

from __future__ import annotations

from pathlib import Path

from core.model_probe import ProbeStore, classify_probe


def test_classify_live_from_real_content() -> None:
    chunks = [
        'event: content_block_delta\ndata: {"type":"content_block_delta",'
        '"delta":{"type":"text_delta","text":"ok"}}\n\n'
    ]
    verdict = classify_probe(chunks, None)
    assert verdict == {"status": "live", "kind": "live", "error": None}


class _HttpError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def test_classify_rate_limit_is_temporary() -> None:
    verdict = classify_probe([], _HttpError("too many requests", 429))
    assert verdict["status"] == "down"
    assert verdict["kind"] == "rate_limited"  # temporary → "Busy — retry later"
    assert "429" in verdict["error"]


def test_classify_server_error_is_overloaded() -> None:
    assert classify_probe([], _HttpError("bad gateway", 503))["kind"] == "overloaded"


def test_classify_auth_and_notfound_are_unavailable() -> None:
    assert classify_probe([], _HttpError("forbidden", 403))["kind"] == "unavailable"
    assert classify_probe([], _HttpError("nope", 404))["kind"] == "unavailable"


def test_classify_connection_error_is_unreachable() -> None:
    class ConnectTimeout(Exception):
        pass

    assert classify_probe([], ConnectTimeout("boom"))["kind"] == "unreachable"


def test_classify_stream_error_event_uses_message_kind() -> None:
    chunks = [
        'event: error\ndata: {"type":"error",'
        '"error":{"type":"not_found_error","message":"Model x does not exist"}}\n\n'
    ]
    verdict = classify_probe(chunks, None)
    assert verdict["status"] == "down"
    assert verdict["kind"] == "unavailable"
    assert "does not exist" in verdict["error"]


def test_classify_down_on_empty_stream() -> None:
    assert classify_probe([], None) == {
        "status": "down",
        "kind": "error",
        "error": "empty response",
    }


def test_probe_store_records_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "probes.json"
    store = ProbeStore(path=path)
    entry = store.record(
        "cerebras", "gpt-oss-120b", {"status": "live", "latency_ms": 42}
    )
    assert entry["status"] == "live"
    assert "at" in entry  # timestamp stamped on record
    got = store.get("cerebras", "gpt-oss-120b")
    assert got is not None and got["latency_ms"] == 42
    assert store.get("groq", "missing") is None

    # A fresh store loads the same results from disk (survives restart).
    reloaded = ProbeStore(path=path)
    reloaded_entry = reloaded.get("cerebras", "gpt-oss-120b")
    assert reloaded_entry is not None and reloaded_entry["status"] == "live"


def test_probe_store_tolerates_missing_and_corrupt_file(tmp_path: Path) -> None:
    missing = ProbeStore(path=tmp_path / "nope.json")
    assert missing.snapshot() == {}

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not valid json", encoding="utf-8")
    assert ProbeStore(path=corrupt).snapshot() == {}
