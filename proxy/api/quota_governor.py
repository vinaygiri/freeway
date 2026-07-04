"""Quota Governor — compares live consumption to known limits.

Sits above the neutral :class:`~core.quota.QuotaTracker` (usage data) and the
:mod:`config.provider_quota` limit catalog, producing a per-provider verdict:
utilization, status, and a proactive ``avoid`` flag the router can use to steer
requests away from a provider *before* it 429s. Lives in ``api`` because it
bridges ``core`` and ``config`` (which may not import each other).
"""

from __future__ import annotations

from collections.abc import Mapping

from config.provider_quota import PROVIDER_QUOTA_LIMITS, ProviderQuotaLimit
from core.quota import RPM_WINDOW_S, QuotaTracker

# Utilization thresholds (fraction of the tightest known limit).
WARN_UTILIZATION = 0.8
AVOID_UTILIZATION = 0.95


class QuotaGovernor:
    """Assess per-provider quota headroom from tracked consumption."""

    def __init__(
        self,
        tracker: QuotaTracker,
        limits: Mapping[str, ProviderQuotaLimit] = PROVIDER_QUOTA_LIMITS,
    ) -> None:
        self._tracker = tracker
        self._limits = limits

    def assess(self, provider_id: str) -> dict[str, object]:
        usage = self._tracker.usage(provider_id)
        limit = self._limits.get(provider_id)
        dimensions: dict[str, dict[str, float]] = {}
        if limit is not None:
            self._add_dimension(
                dimensions, "rpm", usage["requests_last_minute"], limit.rpm
            )
            self._add_dimension(
                dimensions,
                "requests_per_day",
                usage["requests_last_day"],
                limit.requests_per_day,
            )
            self._add_dimension(
                dimensions,
                "tokens_per_day",
                usage["input_tokens_last_day"],
                limit.tokens_per_day,
            )

        if not dimensions:
            return {
                "provider": provider_id,
                "status": "unknown",
                "utilization": None,
                "dimensions": {},
                "seconds_to_exhaustion": None,
                "avoid": False,
            }

        worst = max(dim["utilization"] for dim in dimensions.values())
        return {
            "provider": provider_id,
            "status": self._status(worst),
            "utilization": round(worst, 3),
            "dimensions": dimensions,
            "seconds_to_exhaustion": self._seconds_to_exhaustion(usage, dimensions),
            "avoid": worst >= AVOID_UTILIZATION,
        }

    def should_avoid(self, provider_id: str) -> bool:
        return bool(self.assess(provider_id)["avoid"])

    def snapshot(self) -> dict[str, dict[str, object]]:
        provider_ids = set(self._tracker.providers()) | set(self._limits)
        return {provider_id: self.assess(provider_id) for provider_id in provider_ids}

    @staticmethod
    def _add_dimension(
        dimensions: dict[str, dict[str, float]],
        name: str,
        used: int,
        cap: int | None,
    ) -> None:
        if cap is None or cap <= 0:
            return
        dimensions[name] = {
            "used": used,
            "limit": cap,
            "remaining": max(0, cap - used),
            "utilization": round(used / cap, 3),
        }

    @staticmethod
    def _status(worst: float) -> str:
        if worst >= 1.0:
            return "exhausted"
        if worst >= WARN_UTILIZATION:
            return "warning"
        return "ok"

    @staticmethod
    def _seconds_to_exhaustion(
        usage: Mapping[str, int], dimensions: Mapping[str, dict[str, float]]
    ) -> float | None:
        """Project seconds until the day-scale request budget is exhausted.

        Uses the current per-minute request rate; returns ``None`` when idle or
        when there is no day-scale request cap to project against.
        """
        rate_per_second = usage["requests_last_minute"] / RPM_WINDOW_S
        day = dimensions.get("requests_per_day")
        if day is None or rate_per_second <= 0 or day["remaining"] <= 0:
            return None
        return round(day["remaining"] / rate_per_second, 1)
