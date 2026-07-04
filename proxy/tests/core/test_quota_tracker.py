from __future__ import annotations

from core.quota import QuotaTracker


class _Clock:
    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_records_and_counts_rolling_windows():
    tracker = QuotaTracker(now=_Clock())
    for _ in range(5):
        tracker.record_request("groq", input_tokens=10)
    usage = tracker.usage("groq")
    assert usage == {
        "requests_last_minute": 5,
        "requests_last_day": 5,
        "input_tokens_last_day": 50,
    }


def test_minute_window_expires_but_day_window_holds():
    clock = _Clock()
    tracker = QuotaTracker(now=clock)
    tracker.record_request("groq")
    clock.advance(61)  # push the first event out of the 60s window
    tracker.record_request("groq")
    usage = tracker.usage("groq")
    assert usage["requests_last_minute"] == 1
    assert usage["requests_last_day"] == 2


def test_day_window_expires():
    clock = _Clock()
    tracker = QuotaTracker(now=clock)
    tracker.record_request("groq", input_tokens=100)
    clock.advance(86_401)
    usage = tracker.usage("groq")
    assert usage["requests_last_day"] == 0
    assert usage["input_tokens_last_day"] == 0


def test_unknown_provider_has_zero_usage():
    assert QuotaTracker().usage("nope") == {
        "requests_last_minute": 0,
        "requests_last_day": 0,
        "input_tokens_last_day": 0,
    }


def test_providers_lists_recorded_targets():
    tracker = QuotaTracker()
    tracker.record_request("groq")
    tracker.record_request("nvidia_nim")
    assert set(tracker.providers()) == {"groq", "nvidia_nim"}
