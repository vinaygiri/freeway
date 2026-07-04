"""Data-governance governor — enforces the user's trust policy at routing time.

Bridges the per-provider data-policy catalog (:mod:`config.provider_policy`) and
the user's policy settings. Unlike the health/quota signals (which *deprioritize*),
a trust violation is a **hard exclusion**: the router must never send a request to
a provider that violates the policy, even as a last resort — better to fail than
to leak code. Unknown data policy is treated as non-compliant under a strict
setting (fail safe).
"""

from __future__ import annotations

from collections.abc import Iterable

from config.provider_catalog import PROVIDER_CATALOG
from config.provider_policy import PROVIDER_DATA_POLICIES, ProviderDataPolicy
from config.settings import Settings

# Providers that run locally and never egress prompts.
LOCAL_PROVIDER_IDS = frozenset(
    provider_id
    for provider_id, descriptor in PROVIDER_CATALOG.items()
    if "local" in descriptor.capabilities
)


class DataGovernor:
    """Decide whether a provider satisfies the active data-governance policy."""

    def __init__(
        self,
        *,
        require_no_training: bool = False,
        require_local_only: bool = False,
        allowed_regions: Iterable[str] = (),
        policies: dict[str, ProviderDataPolicy] | None = None,
        local_provider_ids: Iterable[str] = LOCAL_PROVIDER_IDS,
    ) -> None:
        self._require_no_training = require_no_training
        self._require_local_only = require_local_only
        self._allowed_regions = frozenset(
            region.strip().lower() for region in allowed_regions if region.strip()
        )
        self._policies = policies if policies is not None else PROVIDER_DATA_POLICIES
        self._local_ids = frozenset(local_provider_ids)

    @classmethod
    def from_settings(cls, settings: Settings) -> DataGovernor:
        raw_regions = getattr(settings, "allowed_regions", "") or ""
        return cls(
            require_no_training=bool(getattr(settings, "require_no_training", False)),
            require_local_only=bool(getattr(settings, "require_local_only", False)),
            allowed_regions=[r for r in raw_regions.split(",") if r.strip()],
        )

    @property
    def active(self) -> bool:
        return bool(
            self._require_no_training
            or self._require_local_only
            or self._allowed_regions
        )

    def reason(self, provider_id: str) -> str | None:
        """Return why a provider is blocked by policy, or ``None`` when compliant."""
        is_local = provider_id in self._local_ids
        policy = self._policies.get(provider_id)

        if self._require_local_only and not is_local:
            return "local_only"
        if self._require_no_training:
            trains = policy.trains_on_prompts if policy is not None else None
            # Blocked when it trains, or when the policy is unknown (fail safe).
            if trains is not False:
                return "training"
        if self._allowed_regions:
            region = (policy.region if policy is not None else None) or ""
            if region.lower() not in self._allowed_regions:
                return "region"
        return None

    def allowed(self, provider_id: str) -> bool:
        return self.reason(provider_id) is None
