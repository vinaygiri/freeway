from __future__ import annotations

from core.health.score import (
    NO_DATA,
    Sample,
    jitter,
    p95_latency,
    stability_score,
    verdict,
)


def _latency_samples(latencies: list[float], code: str = "200") -> list[Sample]:
    return [Sample(code=code, latency_ms=ms) for ms in latencies]


# -- p95 --------------------------------------------------------------------
def test_p95_none_without_measurable_samples():
    assert p95_latency([]) is None
    assert p95_latency([Sample(code="ERR")]) is None


def test_p95_index_for_four_samples_is_the_max():
    # ceil(4 * 0.95) - 1 = 3 -> the 4th (largest) element.
    assert p95_latency(_latency_samples([100, 200, 300, 400])) == 400


def test_p95_catches_tail_spike_across_twenty_samples():
    samples = _latency_samples([100] * 18 + [6000, 6000])
    assert p95_latency(samples) == 6000


# -- jitter -----------------------------------------------------------------
def test_jitter_zero_with_fewer_than_two_samples():
    assert jitter([]) == 0
    assert jitter(_latency_samples([100])) == 0


def test_jitter_is_population_stddev():
    assert jitter(_latency_samples([100, 300])) == 100.0


def test_jitter_includes_401_latency_samples():
    samples = [Sample(code="200", latency_ms=100), Sample(code="401", latency_ms=300)]
    assert jitter(samples) == 100.0


# -- stability score --------------------------------------------------------
def test_stability_no_data_without_measurable_samples():
    assert stability_score([]) == NO_DATA
    assert stability_score([Sample(code="ERR"), Sample(code="000")]) == NO_DATA


def test_stability_high_for_consistent_fast_model():
    assert stability_score(_latency_samples([250] * 10)) >= 80


def test_stability_scores_401_latency_samples():
    score = stability_score(_latency_samples([250] * 10, code="401"))
    assert 0 < score <= 100


def test_stability_low_for_spiky_model():
    samples = _latency_samples([100] * 18 + [7000, 7000])
    assert stability_score(samples) < 60


def test_stability_uptime_penalty():
    healthy = _latency_samples([200] * 10)
    with_failures = [
        *_latency_samples([200] * 8),
        Sample(code="ERR"),
        Sample(code="ERR"),
    ]
    assert stability_score(with_failures) < stability_score(healthy)


def test_stability_steady_model_beats_spiky_model():
    model_a = _latency_samples([100] * 18 + [6000, 6000])  # spiky tail
    model_b = _latency_samples([400] * 20)  # steady
    assert stability_score(model_b) > stability_score(model_a)


def test_stability_always_in_range():
    for samples in (
        _latency_samples([250] * 5),
        _latency_samples([100] * 18 + [7000, 7000]),
        _latency_samples([4999] * 3),
    ):
        assert 0 <= stability_score(samples) <= 100


# -- verdict ----------------------------------------------------------------
def test_verdict_pending_without_samples():
    assert verdict([]) == "Pending"


def test_verdict_perfect_for_fast_and_stable():
    assert verdict(_latency_samples([205] * 5)) == "Perfect"


def test_verdict_spiky_for_normal_avg_but_terrible_p95():
    samples = _latency_samples([200] * 18 + [8000, 8000])
    assert verdict(samples) == "Spiky"


def test_verdict_overloaded_on_last_429():
    samples = [*_latency_samples([200] * 3), Sample(code="429", latency_ms=150)]
    assert verdict(samples) == "Overloaded"


def test_verdict_not_active_when_never_up():
    assert verdict([Sample(code="ERR"), Sample(code="000")]) == "Not Active"


def test_verdict_unstable_when_previously_up_then_failing():
    samples = [Sample(code="200", latency_ms=200), Sample(code="ERR")]
    assert verdict(samples) == "Unstable"
