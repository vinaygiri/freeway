"""Tests for the descriptor-driven generic OpenAI-compatible provider union."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from config.provider_catalog import PROVIDER_CATALOG
from config.settings import Settings
from providers.base import ProviderConfig
from providers.generic_openai_chat import GenericOpenAIChatProvider
from providers.runtime import build_provider_config, create_provider
from providers.runtime.factory import PROVIDER_FACTORIES

# Providers merged in from the free-coding-models catalog via the generic engine.
_GENERIC_UNION_IDS = (
    "sambanova",
    "novita",
    "ovhcloud",
    "scaleway",
    "alibaba",
    "github_models",
    "ollama_cloud",
    "routeway",
)

_KEY_ATTR = {
    "sambanova": "sambanova_api_key",
    "novita": "novita_api_key",
    "ovhcloud": "ovhcloud_api_key",
    "scaleway": "scaleway_api_key",
    "alibaba": "alibaba_api_key",
    "github_models": "github_models_token",
    "ollama_cloud": "ollama_cloud_api_key",
    "routeway": "routeway_api_key",
}


@pytest.mark.parametrize("provider_id", _GENERIC_UNION_IDS)
def test_union_provider_in_catalog_and_factory(provider_id: str) -> None:
    assert provider_id in PROVIDER_CATALOG
    assert provider_id in PROVIDER_FACTORIES
    desc = PROVIDER_CATALOG[provider_id]
    assert desc.transport_type == "openai_chat"
    assert desc.default_base_url
    assert desc.credential_env
    assert desc.credential_attr == _KEY_ATTR[provider_id]


@pytest.mark.parametrize("provider_id", _GENERIC_UNION_IDS)
def test_union_provider_builds_as_generic(provider_id: str) -> None:
    settings = _make_settings(**{_KEY_ATTR[provider_id]: "test-key"})
    with patch("providers.transports.openai_chat.transport.AsyncOpenAI"):
        provider = create_provider(provider_id, settings)
    assert isinstance(provider, GenericOpenAIChatProvider)


def test_generic_provider_uses_configured_base_url() -> None:
    desc = PROVIDER_CATALOG["sambanova"]
    base = desc.default_base_url
    assert base is not None
    settings = _make_settings(sambanova_api_key="test-key")
    config = build_provider_config(desc, settings)
    assert config.base_url == base

    with patch("providers.transports.openai_chat.transport.AsyncOpenAI"):
        provider = GenericOpenAIChatProvider(
            config, provider_name="SAMBANOVA", base_url=config.base_url or ""
        )
    # Base URL is normalized (trailing slash stripped) on the transport.
    assert provider._base_url == base.rstrip("/")


def test_missing_key_raises_configuration_error() -> None:
    from providers.exceptions import AuthenticationError

    settings = _make_settings()  # no sambanova key
    with pytest.raises(AuthenticationError, match="SAMBANOVA_API_KEY"):
        create_provider("sambanova", settings)


def _make_settings(**overrides: object) -> Settings:
    """Minimal real Settings object for provider construction."""
    settings = Settings()
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


def test_generic_provider_config_is_pooled() -> None:
    """A comma-separated key list becomes a rotation pool (shared transport)."""
    config = ProviderConfig(
        api_key="k1", api_keys=("k1", "k2"), base_url="https://x/v1"
    )
    with patch("providers.transports.openai_chat.transport.AsyncOpenAI"):
        provider = GenericOpenAIChatProvider(
            config, provider_name="ROUTEWAY", base_url="https://x/v1"
        )
    assert provider._key_pool.keys() == ["k1", "k2"]
