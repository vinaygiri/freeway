"""Per-target circuit breaker for provider failover.

Ported from the free-coding-models router daemon: a model/provider key opens
after ``failure_threshold`` consecutive failures, stays open for an
exponentially backed-off cooldown (30s -> 300s), then goes half-open (routable
again) until the next success closes it or the next failure re-opens it.

Pure and neutral (no api/config/providers imports); the clock is injectable for
deterministic tests. Single-event-loop use, so no locking.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"

FAILURE_THRESHOLD = 3
INITIAL_COOLDOWN_S = 30.0
MAX_COOLDOWN_S = 300.0
BACKOFF_MULTIPLIER = 2.0


@dataclass(slots=True)
class _CircuitState:
    state: str = CLOSED
    consecutive_failures: int = 0
    cooldown_s: float = INITIAL_COOLDOWN_S
    opened_at: float | None = None


class CircuitBreaker:
    """Track per-target circuit state; app-scoped and shared across requests."""

    def __init__(
        self,
        *,
        now: Callable[[], float] = time.monotonic,
        failure_threshold: int = FAILURE_THRESHOLD,
        initial_cooldown_s: float = INITIAL_COOLDOWN_S,
        max_cooldown_s: float = MAX_COOLDOWN_S,
        backoff_multiplier: float = BACKOFF_MULTIPLIER,
    ) -> None:
        self._now = now
        self._threshold = failure_threshold
        self._initial_cooldown_s = initial_cooldown_s
        self._max_cooldown_s = max_cooldown_s
        self._backoff = backoff_multiplier
        self._states: dict[str, _CircuitState] = {}

    def is_routable(self, key: str) -> bool:
        """Return whether ``key`` may be tried now (lazily half-opens on cooldown)."""
        state = self._states.get(key)
        if state is None or state.state == CLOSED:
            return True
        if state.state == OPEN:
            if (
                state.opened_at is not None
                and self._now() - state.opened_at >= state.cooldown_s
            ):
                state.state = HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN is routable (a probe attempt)

    def record_failure(self, key: str) -> None:
        state = self._states.setdefault(key, _CircuitState())
        state.consecutive_failures += 1
        if state.state == HALF_OPEN:
            # A failed half-open probe re-opens the circuit with a longer cooldown.
            state.state = OPEN
            state.opened_at = self._now()
            state.cooldown_s = min(
                self._max_cooldown_s, state.cooldown_s * self._backoff
            )
        elif state.consecutive_failures >= self._threshold:
            # First open uses the initial cooldown.
            state.state = OPEN
            state.opened_at = self._now()

    def record_success(self, key: str) -> None:
        state = self._states.setdefault(key, _CircuitState())
        state.state = CLOSED
        state.consecutive_failures = 0
        state.cooldown_s = self._initial_cooldown_s
        state.opened_at = None

    def state_of(self, key: str) -> str:
        """Return the current state (routability check first so OPEN can half-open)."""
        self.is_routable(key)
        state = self._states.get(key)
        return state.state if state is not None else CLOSED

    def snapshot(self) -> dict[str, dict[str, object]]:
        return {
            key: {
                "state": self.state_of(key),
                "consecutive_failures": state.consecutive_failures,
                "cooldown_s": state.cooldown_s,
            }
            for key, state in self._states.items()
        }
