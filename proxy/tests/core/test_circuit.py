from __future__ import annotations

from core.circuit import CircuitBreaker


class _Clock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_unknown_key_is_routable_and_closed():
    breaker = CircuitBreaker()
    assert breaker.is_routable("groq/x") is True
    assert breaker.state_of("groq/x") == "closed"


def test_opens_after_threshold_failures():
    breaker = CircuitBreaker(now=_Clock())
    for _ in range(3):
        breaker.record_failure("groq/x")
    assert breaker.state_of("groq/x") == "open"
    assert breaker.is_routable("groq/x") is False


def test_half_opens_after_cooldown_then_closes_on_success():
    clock = _Clock()
    breaker = CircuitBreaker(now=clock)
    for _ in range(3):
        breaker.record_failure("groq/x")
    assert breaker.is_routable("groq/x") is False
    clock.advance(31)  # past the 30s initial cooldown
    assert breaker.is_routable("groq/x") is True
    assert breaker.state_of("groq/x") == "half_open"
    breaker.record_success("groq/x")
    assert breaker.state_of("groq/x") == "closed"


def test_failure_in_half_open_reopens_immediately_with_backoff():
    clock = _Clock()
    breaker = CircuitBreaker(now=clock)
    for _ in range(3):
        breaker.record_failure("groq/x")
    clock.advance(31)
    assert breaker.is_routable("groq/x") is True  # half-open
    breaker.record_failure("groq/x")  # one failure while half-open re-opens
    assert breaker.state_of("groq/x") == "open"
    # cooldown backed off from 30 -> 60
    clock.advance(31)
    assert breaker.is_routable("groq/x") is False  # still open (needs 60s)
    clock.advance(30)
    assert breaker.is_routable("groq/x") is True


def test_success_resets_failure_count():
    breaker = CircuitBreaker()
    breaker.record_failure("groq/x")
    breaker.record_failure("groq/x")
    breaker.record_success("groq/x")
    breaker.record_failure("groq/x")
    assert breaker.state_of("groq/x") == "closed"  # counter reset, only 1 fresh failure


def test_snapshot_reports_state():
    breaker = CircuitBreaker()
    breaker.record_failure("groq/x")
    snap = breaker.snapshot()
    assert snap["groq/x"]["state"] == "closed"
    assert snap["groq/x"]["consecutive_failures"] == 1
