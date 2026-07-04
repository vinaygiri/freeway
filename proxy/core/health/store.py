"""In-memory per-target health store backing the benchmark/health plane.

Holds a bounded ring buffer of recent :class:`Sample` observations per target
(a provider id, or later a ``provider/model`` ref) and exposes computed health
summaries. Bounding the window is a deliberate improvement over the unbounded
sample history in the upstream free-coding-models client.

Single-event-loop use only: the probe task and the read endpoints all run on the
asyncio loop, and neither ``record`` nor ``snapshot`` awaits, so no lock is
needed.
"""

from __future__ import annotations

from collections import deque

from .score import Sample, summarize

DEFAULT_WINDOW = 100


class HealthStore:
    """Bounded per-target latency/health sample store."""

    def __init__(self, *, window: int = DEFAULT_WINDOW) -> None:
        self._window = max(1, window)
        self._samples: dict[str, deque[Sample]] = {}

    def record(self, target: str, sample: Sample) -> None:
        buffer = self._samples.get(target)
        if buffer is None:
            buffer = deque(maxlen=self._window)
            self._samples[target] = buffer
        buffer.append(sample)

    def targets(self) -> list[str]:
        return list(self._samples)

    def samples(self, target: str) -> list[Sample]:
        return list(self._samples.get(target, ()))

    def summary(self, target: str) -> dict[str, object] | None:
        buffer = self._samples.get(target)
        if buffer is None:
            return None
        return summarize(list(buffer))

    def snapshot(self) -> dict[str, dict[str, object]]:
        return {
            target: summarize(list(buffer)) for target, buffer in self._samples.items()
        }
