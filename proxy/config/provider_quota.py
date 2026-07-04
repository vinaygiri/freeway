"""Known free-tier quota limits per provider.

Reference data ported from the free-coding-models catalog/README. Values are
best-effort and conservative (e.g. Groq's per-day request cap varies by model,
so the low end is used). ``None`` means "no published limit / unknown", in
which case the quota governor treats that dimension as unconstrained.

This module is intentionally self-contained (no imports from other layers) to
respect the config import boundary.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderQuotaLimit:
    """Free-tier limits for one provider. ``None`` == unknown/unconstrained."""

    provider_id: str
    rpm: int | None = None
    requests_per_day: int | None = None
    tokens_per_day: int | None = None
    notes: str = ""


# Keyed by the proxy's provider ids (see config.provider_ids). Providers with no
# entry (deepseek, kimi, wafer, fireworks, gemini, mistral, zai, opencode*, and
# the local lmstudio/llamacpp/ollama) have no published free-tier caps to model.
PROVIDER_QUOTA_LIMITS: dict[str, ProviderQuotaLimit] = {
    "nvidia_nim": ProviderQuotaLimit(
        provider_id="nvidia_nim", rpm=40, notes="~40 RPM, no credit card"
    ),
    "groq": ProviderQuotaLimit(
        provider_id="groq",
        rpm=30,
        requests_per_day=1000,
        notes="30 RPM; per-day cap varies 1K-14.4K by model (low end used)",
    ),
    "cerebras": ProviderQuotaLimit(
        provider_id="cerebras",
        rpm=30,
        tokens_per_day=1_000_000,
        notes="30 RPM, 1M tokens/day",
    ),
    "open_router": ProviderQuotaLimit(
        provider_id="open_router",
        rpm=20,
        requests_per_day=50,
        notes="50 req/day free (1000 with >=$10 spend); resets UTC midnight",
    ),
    "codestral": ProviderQuotaLimit(
        provider_id="codestral",
        rpm=30,
        requests_per_day=2000,
        notes="30 RPM, 2000 req/day",
    ),
    "cloudflare": ProviderQuotaLimit(
        provider_id="cloudflare",
        rpm=300,
        notes="300 RPM; daily cap is 10K neurons (not modeled as tokens)",
    ),
}


def quota_limit_for(provider_id: str) -> ProviderQuotaLimit | None:
    """Return known quota limits for a provider, or ``None`` when unknown."""
    return PROVIDER_QUOTA_LIMITS.get(provider_id)
