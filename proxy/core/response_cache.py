"""Bounded exact-match response cache for replaying identical requests.

Stores the raw Anthropic-SSE chunk list for a completed response, keyed by a
hash of the semantically-relevant request fields, so an identical follow-up
request replays instantly and spends zero provider quota. Bounded LRU + TTL.

Neutral (string keys + opaque SSE chunks): no api/config imports. The capture
helper commits to the cache **only on clean completion** — never on a client
disconnect, cancellation, or mid-stream failure — so a truncated stream is
never cached and replayed forever.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import AsyncGenerator, AsyncIterator, Callable

DEFAULT_WINDOW = 256
DEFAULT_TTL_SECONDS = 300.0
_TERMINAL_MARKER = "message_stop"


class ResponseCache:
    """LRU + TTL cache of completed Anthropic-SSE responses, keyed by request hash."""

    def __init__(
        self,
        *,
        window: int = DEFAULT_WINDOW,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._window = max(1, window)
        self._ttl = ttl_seconds
        self._now = now
        self._entries: OrderedDict[str, tuple[float, list[str]]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> list[str] | None:
        entry = self._entries.get(key)
        if entry is None:
            self._misses += 1
            return None
        expires_at, chunks = entry
        if self._now() >= expires_at:
            del self._entries[key]
            self._misses += 1
            return None
        self._entries.move_to_end(key)
        self._hits += 1
        return list(chunks)

    def put(self, key: str, chunks: list[str]) -> None:
        self._entries[key] = (self._now() + self._ttl, list(chunks))
        self._entries.move_to_end(key)
        while len(self._entries) > self._window:
            self._entries.popitem(last=False)

    def snapshot(self) -> dict[str, int]:
        return {
            "entries": len(self._entries),
            "hits": self._hits,
            "misses": self._misses,
        }

    def clear(self) -> None:
        """Drop all cached entries and reset hit/miss counters."""
        self._entries.clear()
        self._hits = 0
        self._misses = 0


async def replay(chunks: list[str]) -> AsyncIterator[str]:
    """Re-yield cached SSE chunks as a fresh stream."""
    for chunk in chunks:
        yield chunk


async def capture_and_cache(
    source: AsyncIterator[str], cache: ResponseCache, key: str
) -> AsyncGenerator[str]:
    """Pass SSE chunks through unchanged; cache them only on clean completion.

    Commits to the cache only when the source iterator is fully consumed AND a
    terminal ``message_stop`` event was seen — never on GeneratorExit (client
    disconnect), cancellation, or a mid-stream error.
    """
    chunks: list[str] = []
    completed = False
    try:
        async for chunk in source:
            chunks.append(chunk)
            yield chunk
        completed = True
    finally:
        if completed and any(_TERMINAL_MARKER in chunk for chunk in chunks):
            cache.put(key, chunks)
