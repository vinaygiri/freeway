"""Per-provider data-governance tags for trust-aware routing.

Best-effort, conservative reference data: does a provider train on prompts, and
what region does it serve. ``None`` means "unknown" — and under a strict user
policy, unknown is treated as *not* satisfying the requirement (fail safe: don't
send code where the data policy is unclear). Local providers never egress.

Self-contained (config layer): no imports from other layers. Always verify the
current provider terms for high-stakes use.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderDataPolicy:
    """Data-handling tags for one provider. ``None`` == unknown."""

    provider_id: str
    trains_on_prompts: bool | None = None
    region: str | None = None


# Only entries we can state with reasonable confidence. Local providers do not
# egress at all. Everything absent here is "unknown" (treated conservatively).
PROVIDER_DATA_POLICIES: dict[str, ProviderDataPolicy] = {
    # Google AI Studio free tier may use prompts to improve products (per terms).
    "gemini": ProviderDataPolicy("gemini", trains_on_prompts=True, region="global"),
    # Local runtimes — nothing leaves the machine.
    "lmstudio": ProviderDataPolicy("lmstudio", trains_on_prompts=False, region="local"),
    "llamacpp": ProviderDataPolicy("llamacpp", trains_on_prompts=False, region="local"),
    "ollama": ProviderDataPolicy("ollama", trains_on_prompts=False, region="local"),
}


def data_policy_for(provider_id: str) -> ProviderDataPolicy | None:
    """Return known data-governance tags for a provider, or ``None`` when unknown."""
    return PROVIDER_DATA_POLICIES.get(provider_id)
