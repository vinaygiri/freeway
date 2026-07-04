"""Live per-provider consumption tracking for the Quota Governor.

Records one event per real request (timestamp + input tokens) into a bounded
per-provider buffer and answers rolling-window usage queries (requests in the
last minute / day, input tokens in the last day). Pure and neutral: no imports
from api/config/providers, and the clock is injectable for deterministic tests.

Output-token accounting is intentionally not captured yet (it would require
wrapping the SSE stream); request-rate limits are the dominant free-tier
constraint and are recorded completely and safely here. ``record_request``
already accepts a token count so token accounting can extend this without
reshaping the API.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

RPM_WINDOW_S = 60.0
DAY_WINDOW_S = 86_400.0
DEFAULT_MAX_EVENTS = 100_000


@dataclass(frozen=True, slots=True)
class ConsumptionEvent:
    at: float
    input_tokens: int


class QuotaTracker:
    """Bounded per-provider record of recent request-consumption events."""

    def __init__(
        self,
        *,
        now: Callable[[], float] = time.time,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> None:
        self._now = now
        self._max_events = max(1, max_events)
        self._events: dict[str, deque[ConsumptionEvent]] = {}

    def record_request(self, provider_id: str, *, input_tokens: int = 0) -> None:
        buffer = self._events.get(provider_id)
        if buffer is None:
            buffer = deque(maxlen=self._max_events)
            self._events[provider_id] = buffer
        buffer.append(ConsumptionEvent(self._now(), max(0, input_tokens)))

    def providers(self) -> list[str]:
        return list(self._events)

    def usage(self, provider_id: str) -> dict[str, int]:
        now = self._now()
        buffer = self._events.get(provider_id, ())
        requests_last_minute = 0
        requests_last_day = 0
        input_tokens_last_day = 0
        for event in buffer:
            age = now - event.at
            if age <= DAY_WINDOW_S:
                requests_last_day += 1
                input_tokens_last_day += event.input_tokens
                if age <= RPM_WINDOW_S:
                    requests_last_minute += 1
        return {
            "requests_last_minute": requests_last_minute,
            "requests_last_day": requests_last_day,
            "input_tokens_last_day": input_tokens_last_day,
        }
