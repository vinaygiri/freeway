"""Bounded store of recent routing decisions for the Request Inspector.

Captures, per request, what the client asked for, which provider/model it routed
to and **why** (was it a fallback, and what demoted the primary), the input-token
size, and the terminal-at-route outcome. This is the "glass box": metadata only —
no prompt content — so it is safe to surface locally.

Count-bounded (a ring buffer), so no time-window/clock logic is needed. Recording
happens synchronously at route time (off the streaming path); true mid-stream
success/failure is out of scope here.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass

DEFAULT_WINDOW = 200


@dataclass(frozen=True, slots=True)
class RecentRequest:
    at: float
    request_id: str
    gateway_model: str
    provider_id: str
    provider_model: str
    input_tokens: int
    was_fallback: bool
    candidates_tried: int
    downgrade_reason: str | None
    outcome: str  # "routed" | "eager_error" | "no_candidates"
    error: str | None = None


class RecentRequestStore:
    """Ring buffer of the most recent routing decisions."""

    def __init__(self, *, window: int = DEFAULT_WINDOW) -> None:
        self._records: deque[RecentRequest] = deque(maxlen=max(1, window))

    def record(self, request: RecentRequest) -> None:
        self._records.append(request)

    def snapshot(self) -> list[dict[str, object]]:
        """Return recorded requests, newest first, as JSON-friendly dicts."""
        return [asdict(request) for request in reversed(self._records)]
