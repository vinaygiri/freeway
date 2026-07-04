"""Health/quota/circuit-aware candidate ordering for failover routing.

Bundles the three app-scoped signals — the circuit breaker (``core.circuit``),
the quota governor (``api.quota_governor``), and the health store
(``core.health``) — behind one object the failover executor consumes. A policy
with no signals wired (the default) degrades to "keep configured order, gate
nothing", so direct/test construction of the executor still works.

Ordering rule: dedupe candidates, then put *usable* candidates (circuit
routable, not quota-``avoid``, not health-``Not Active``) first in their
configured order, followed by the rest — so a request is always attempted, but
prefers providers with headroom. This is the proactive "route away before the
429" behavior; it happens at selection time, needing no streaming changes.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from core.circuit import CircuitBreaker
from core.health import HealthStore
from core.recent_requests import RecentRequest, RecentRequestStore
from providers.runtime import ProviderModelInfo

from .data_governor import DataGovernor
from .model_router import ResolvedModel
from .quota_governor import QuotaGovernor

DEFAULT_MAX_ATTEMPTS = 3
_DEAD_VERDICT = "Not Active"

ModelInfoLookup = Callable[[str, str], ProviderModelInfo | None]


class RoutingPolicy:
    """Order and gate failover candidates using live health/quota/circuit state."""

    def __init__(
        self,
        *,
        circuit_breaker: CircuitBreaker | None = None,
        quota_governor: QuotaGovernor | None = None,
        health_store: HealthStore | None = None,
        model_info_lookup: ModelInfoLookup | None = None,
        recent_requests: RecentRequestStore | None = None,
        data_governor: DataGovernor | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        self._circuit = circuit_breaker
        self._quota = quota_governor
        self._health = health_store
        self._model_info_lookup = model_info_lookup
        self._recent_requests = recent_requests
        self._data_governor = data_governor
        self.max_attempts = max(1, max_attempts)

    @staticmethod
    def circuit_key(resolved: ResolvedModel) -> str:
        return f"{resolved.provider_id}/{resolved.provider_model}"

    def order(
        self,
        candidates: list[ResolvedModel],
        *,
        required_tokens: int | None = None,
    ) -> list[ResolvedModel]:
        deduped = _dedupe(candidates)
        # Trust policy is a HARD filter: violating providers are removed entirely
        # (never a last resort). If this empties the list, the request fails —
        # by design, failing is preferable to leaking code to a disallowed provider.
        if self._data_governor is not None and self._data_governor.active:
            deduped = [c for c in deduped if self._data_governor.allowed(c.provider_id)]
        if (
            self._circuit is None
            and self._quota is None
            and self._health is None
            and self._model_info_lookup is None
        ):
            return deduped
        usable = [c for c in deduped if self.is_usable(c)]
        skipped = [c for c in deduped if not self.is_usable(c)]
        if required_tokens is not None and self._model_info_lookup is not None:
            # Deprioritize (never drop) candidates whose known context window is
            # too small for the request; unknown windows are treated as usable.
            fits = [c for c in usable if self._fits_context(c, required_tokens)]
            too_small = [
                c for c in usable if not self._fits_context(c, required_tokens)
            ]
            usable = fits + too_small
        return usable + skipped

    def _fits_context(self, resolved: ResolvedModel, required_tokens: int) -> bool:
        if self._model_info_lookup is None:
            return True
        info = self._model_info_lookup(resolved.provider_id, resolved.provider_model)
        if info is None or info.context_window is None:
            return True
        return info.context_window >= required_tokens

    def is_usable(self, resolved: ResolvedModel) -> bool:
        # Context sufficiency is a soft deprioritize (not a skip), so it is not
        # considered here — only hard skip reasons gate usability.
        return self.classify(resolved) is None

    def classify(
        self, resolved: ResolvedModel, required_tokens: int | None = None
    ) -> str | None:
        """Return why a candidate is skipped/demoted, or ``None`` when usable."""
        if self._data_governor is not None and self._data_governor.active:
            policy_reason = self._data_governor.reason(resolved.provider_id)
            if policy_reason is not None:
                return f"policy:{policy_reason}"
        if self._circuit is not None and not self._circuit.is_routable(
            self.circuit_key(resolved)
        ):
            return "circuit"
        if self._quota is not None and self._quota.should_avoid(resolved.provider_id):
            return "quota"
        if self._health is not None:
            summary = self._health.summary(resolved.provider_id)
            if summary is not None and summary.get("verdict") == _DEAD_VERDICT:
                return "health"
        if required_tokens is not None and not self._fits_context(
            resolved, required_tokens
        ):
            return "context"
        return None

    def record_request(
        self,
        *,
        primary: ResolvedModel,
        served: ResolvedModel | None,
        gateway_model: str,
        input_tokens: int,
        candidates_tried: int,
        outcome: str,
        error: str | None = None,
        required_tokens: int | None = None,
    ) -> None:
        """Record one routing decision into the recent-request store, if installed."""
        if self._recent_requests is None:
            return
        was_fallback = served is not None and served is not primary
        downgrade_reason = (
            self.classify(primary, required_tokens) if was_fallback else None
        )
        self._recent_requests.record(
            RecentRequest(
                at=time.time(),
                request_id=f"req_{uuid.uuid4().hex[:12]}",
                gateway_model=gateway_model,
                provider_id=served.provider_id if served is not None else "",
                provider_model=served.provider_model if served is not None else "",
                input_tokens=input_tokens,
                was_fallback=was_fallback,
                candidates_tried=candidates_tried,
                downgrade_reason=downgrade_reason,
                outcome=outcome,
                error=error,
            )
        )

    def record_failure(self, resolved: ResolvedModel) -> None:
        if self._circuit is not None:
            self._circuit.record_failure(self.circuit_key(resolved))

    def record_success(self, resolved: ResolvedModel) -> None:
        if self._circuit is not None:
            self._circuit.record_success(self.circuit_key(resolved))


def _dedupe(candidates: list[ResolvedModel]) -> list[ResolvedModel]:
    seen: set[tuple[str, str]] = set()
    ordered: list[ResolvedModel] = []
    for candidate in candidates:
        key = (candidate.provider_id, candidate.provider_model)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(candidate)
    return ordered
