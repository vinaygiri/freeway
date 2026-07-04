"""Unit tests for the bounded exact-match response cache."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from core.response_cache import ResponseCache, capture_and_cache, replay


class _Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_put_get_roundtrip_returns_copy() -> None:
    cache = ResponseCache(window=4, ttl_seconds=100, now=_Clock())
    chunks = ["a", "b"]
    cache.put("k", chunks)

    got = cache.get("k")
    assert got == ["a", "b"]
    # Mutating the returned list must not corrupt the stored entry.
    assert got is not None
    got.append("x")
    assert cache.get("k") == ["a", "b"]
    # And mutating the source list after put must not either.
    chunks.append("y")
    assert cache.get("k") == ["a", "b"]


def test_miss_returns_none_and_counts() -> None:
    cache = ResponseCache(now=_Clock())
    assert cache.get("absent") is None
    assert cache.snapshot() == {"entries": 0, "hits": 0, "misses": 1}


def test_hit_and_miss_counters() -> None:
    cache = ResponseCache(now=_Clock())
    cache.put("k", ["v"])
    cache.get("k")
    cache.get("k")
    cache.get("nope")
    snap = cache.snapshot()
    assert snap == {"entries": 1, "hits": 2, "misses": 1}


def test_ttl_expiry_evicts_and_counts_miss() -> None:
    clock = _Clock()
    cache = ResponseCache(ttl_seconds=10, now=clock)
    cache.put("k", ["v"])

    clock.t = 9.9
    assert cache.get("k") == ["v"]

    clock.t = 20.0
    assert cache.get("k") is None
    # Expired entry is removed from the store.
    assert cache.snapshot()["entries"] == 0


def test_lru_eviction_by_window() -> None:
    cache = ResponseCache(window=2, ttl_seconds=100, now=_Clock())
    cache.put("a", ["1"])
    cache.put("b", ["2"])
    # Touch "a" so "b" becomes least-recently-used.
    assert cache.get("a") == ["1"]
    cache.put("c", ["3"])

    assert cache.get("b") is None
    assert cache.get("a") == ["1"]
    assert cache.get("c") == ["3"]


def test_put_refreshes_ttl_and_recency() -> None:
    clock = _Clock()
    cache = ResponseCache(window=4, ttl_seconds=10, now=clock)
    cache.put("k", ["old"])
    clock.t = 8.0
    cache.put("k", ["new"])
    # A re-put resets the TTL window.
    clock.t = 15.0
    assert cache.get("k") == ["new"]


@pytest.mark.asyncio
async def test_replay_yields_all_chunks() -> None:
    out = [chunk async for chunk in replay(["x", "y", "z"])]
    assert out == ["x", "y", "z"]


async def _source(chunks: list[str]) -> AsyncIterator[str]:
    for chunk in chunks:
        yield chunk


@pytest.mark.asyncio
async def test_capture_caches_on_clean_completion() -> None:
    cache = ResponseCache(now=_Clock())
    chunks = ["start", "message_stop event"]
    out = [c async for c in capture_and_cache(_source(chunks), cache, "k")]

    assert out == chunks
    assert cache.get("k") == chunks


@pytest.mark.asyncio
async def test_capture_does_not_cache_without_terminal_marker() -> None:
    cache = ResponseCache(now=_Clock())
    out = [c async for c in capture_and_cache(_source(["start", "middle"]), cache, "k")]

    assert out == ["start", "middle"]
    assert cache.get("k") is None


@pytest.mark.asyncio
async def test_capture_does_not_cache_on_client_disconnect() -> None:
    cache = ResponseCache(now=_Clock())
    gen = capture_and_cache(_source(["start", "message_stop"]), cache, "k")

    # Consume only the first chunk, then close early (client disconnect).
    first = await gen.__anext__()
    assert first == "start"
    await gen.aclose()

    assert cache.get("k") is None


@pytest.mark.asyncio
async def test_capture_does_not_cache_on_mid_stream_error() -> None:
    cache = ResponseCache(now=_Clock())

    async def _boom() -> AsyncIterator[str]:
        yield "start"
        yield "message_stop"
        raise RuntimeError("upstream blew up")

    with pytest.raises(RuntimeError):
        _ = [c async for c in capture_and_cache(_boom(), cache, "k")]

    assert cache.get("k") is None
