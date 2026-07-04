from __future__ import annotations

from config.provider_quota import PROVIDER_QUOTA_LIMITS, quota_limit_for


def test_known_limits_match_catalog():
    nvidia = quota_limit_for("nvidia_nim")
    openrouter = quota_limit_for("open_router")
    cerebras = quota_limit_for("cerebras")
    codestral = quota_limit_for("codestral")
    cloudflare = quota_limit_for("cloudflare")
    assert nvidia is not None and nvidia.rpm == 40
    assert openrouter is not None and openrouter.requests_per_day == 50
    assert cerebras is not None and cerebras.tokens_per_day == 1_000_000
    assert codestral is not None and codestral.requests_per_day == 2000
    assert cloudflare is not None and cloudflare.rpm == 300


def test_unknown_providers_return_none():
    # FCC-specific / uncapped providers are intentionally absent.
    assert quota_limit_for("deepseek") is None
    assert quota_limit_for("ollama") is None
    assert quota_limit_for("does-not-exist") is None


def test_all_entries_are_self_consistent():
    for provider_id, limit in PROVIDER_QUOTA_LIMITS.items():
        assert limit.provider_id == provider_id
