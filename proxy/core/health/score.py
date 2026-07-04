"""Model health scoring — a faithful Python port of the free-coding-models
stability score.

The stability score is a weighted 0-100 composite of four normalized
components (p95 latency 30%, jitter 30%, spike rate 20%, uptime 20%). Latency
is only counted from "measurable" samples — those that produced a real
round-trip time (HTTP 200 or 401; a 401 still proves the endpoint is reachable).
Errors and timeouts lower uptime but are excluded from latency statistics.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# Component thresholds (milliseconds) and weights — ported verbatim.
P95_THRESHOLD_MS = 5000.0
JITTER_THRESHOLD_MS = 2000.0
SPIKE_THRESHOLD_MS = 3000.0
P95_WEIGHT = 0.3
JITTER_WEIGHT = 0.3
SPIKE_WEIGHT = 0.2
UPTIME_WEIGHT = 0.2

# HTTP status codes that yield a usable latency sample.
MEASURABLE_CODES = frozenset({"200", "401"})

# Returned by :func:`stability_score` when there is no measurable data yet.
NO_DATA = -1


@dataclass(frozen=True, slots=True)
class Sample:
    """One health observation for a target (a provider or provider/model)."""

    code: str
    latency_ms: float | None = None

    @property
    def measurable(self) -> bool:
        return self.code in MEASURABLE_CODES and self.latency_ms is not None


def _measurable_latencies(samples: Sequence[Sample]) -> list[float]:
    return [s.latency_ms for s in samples if s.measurable and s.latency_ms is not None]


def average_latency(samples: Sequence[Sample]) -> float | None:
    latencies = _measurable_latencies(samples)
    if not latencies:
        return None
    return sum(latencies) / len(latencies)


def uptime(samples: Sequence[Sample]) -> int:
    """Percentage (0-100) of samples that returned HTTP 200."""
    if not samples:
        return 0
    successes = sum(1 for s in samples if s.code == "200")
    return round(successes / len(samples) * 100)


def p95_latency(samples: Sequence[Sample]) -> float | None:
    latencies = sorted(_measurable_latencies(samples))
    if not latencies:
        return None
    index = max(0, math.ceil(len(latencies) * 0.95) - 1)
    return latencies[index]


def jitter(samples: Sequence[Sample]) -> float:
    """Population standard deviation of measurable latencies (0 if < 2 samples)."""
    latencies = _measurable_latencies(samples)
    if len(latencies) < 2:
        return 0.0
    mean = sum(latencies) / len(latencies)
    variance = sum((value - mean) ** 2 for value in latencies) / len(latencies)
    return math.sqrt(variance)


def spike_rate(samples: Sequence[Sample]) -> float:
    """Fraction (0-1) of measurable samples slower than the spike threshold."""
    latencies = _measurable_latencies(samples)
    if not latencies:
        return 0.0
    spikes = sum(1 for value in latencies if value > SPIKE_THRESHOLD_MS)
    return spikes / len(latencies)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def stability_score(samples: Sequence[Sample]) -> int:
    """Composite 0-100 stability score, or ``NO_DATA`` (-1) when no measurable data."""
    if not _measurable_latencies(samples):
        return NO_DATA
    p95 = p95_latency(samples) or 0.0
    p95_score = _clamp(100.0 * (1.0 - p95 / P95_THRESHOLD_MS))
    jitter_score = _clamp(100.0 * (1.0 - jitter(samples) / JITTER_THRESHOLD_MS))
    spike_score = _clamp(100.0 * (1.0 - spike_rate(samples)))
    reliability_score = float(uptime(samples))
    score = (
        P95_WEIGHT * p95_score
        + JITTER_WEIGHT * jitter_score
        + SPIKE_WEIGHT * spike_score
        + UPTIME_WEIGHT * reliability_score
    )
    return round(score)


def verdict(samples: Sequence[Sample]) -> str:
    """Human-readable health label derived from the sample history."""
    if not samples:
        return "Pending"
    last = samples[-1]
    if last.code == "429":
        return "Overloaded"
    ever_up = any(s.code == "200" for s in samples)
    if not last.measurable:
        return "Unstable" if ever_up else "Not Active"
    avg = average_latency(samples)
    if avg is None:
        return "Pending"
    measurable_count = len(_measurable_latencies(samples))
    p95 = p95_latency(samples) or 0.0
    if avg < 400:
        if measurable_count >= 3 and p95 > 3000:
            return "Spiky"
        return "Perfect"
    if avg < 1000:
        if measurable_count >= 3 and p95 > 5000:
            return "Spiky"
        return "Normal"
    if avg < 3000:
        return "Slow"
    if avg < 5000:
        return "Very Slow"
    return "Unstable"


def summarize(samples: Sequence[Sample]) -> dict[str, object]:
    """Return a JSON-friendly health summary for one target."""
    avg = average_latency(samples)
    p95 = p95_latency(samples)
    return {
        "sample_count": len(samples),
        "avg_ms": round(avg) if avg is not None else None,
        "p95_ms": round(p95) if p95 is not None else None,
        "jitter_ms": round(jitter(samples)),
        "uptime": uptime(samples),
        "spike_rate": round(spike_rate(samples), 3),
        "stability_score": stability_score(samples),
        "verdict": verdict(samples),
        "last_code": samples[-1].code if samples else None,
    }
