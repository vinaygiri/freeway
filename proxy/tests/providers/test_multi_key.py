from __future__ import annotations

from typing import Any

from config.provider_catalog import PROVIDER_CATALOG
from config.settings import Settings
from providers.base import ProviderConfig
from providers.runtime.config import build_provider_config
from providers.transports.anthropic_messages import AnthropicMessagesTransport
from providers.transports.openai_chat import OpenAIChatTransport


class _NativeProbe(AnthropicMessagesTransport):
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, provider_name="T", default_base_url="http://x")


class _ChatProbe(OpenAIChatTransport):
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(
            config, provider_name="T", base_url="http://x", api_key=config.api_key
        )

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        return {}


# -- config -----------------------------------------------------------------
def test_provider_config_defaults_key_pool_from_single_key():
    assert ProviderConfig(api_key="solo").api_keys == ("solo",)


def test_provider_config_keeps_explicit_pool():
    config = ProviderConfig(api_key="k1", api_keys=("k1", "k2"))
    assert config.api_keys == ("k1", "k2")


def test_build_provider_config_splits_comma_separated_keys():
    settings = Settings()
    settings.groq_api_key = "k1, k2 , k3"
    config = build_provider_config(PROVIDER_CATALOG["groq"], settings)
    assert config.api_keys == ("k1", "k2", "k3")
    assert config.api_key == "k1"  # primary is the first


# -- native transport rotates via the pool-backed property ------------------
def test_native_transport_rotates_api_key():
    provider = _NativeProbe(ProviderConfig(api_key="k1", api_keys=("k1", "k2", "k3")))
    assert [provider._api_key for _ in range(4)] == ["k1", "k2", "k3", "k1"]


def test_native_transport_single_key_is_stable():
    provider = _NativeProbe(ProviderConfig(api_key="solo"))
    assert [provider._api_key for _ in range(3)] == ["solo", "solo", "solo"]


# -- openai-chat transport builds one client per key ------------------------
def test_openai_chat_builds_one_client_per_key_and_rotates():
    provider = _ChatProbe(ProviderConfig(api_key="k1", api_keys=("k1", "k2")))
    assert set(provider._clients) == {"k1", "k2"}
    assert provider._clients["k1"].api_key == "k1"
    assert provider._clients["k2"].api_key == "k2"
    # selection rotates across the per-key clients
    first = provider._select_client()
    second = provider._select_client()
    assert first is provider._clients["k1"]
    assert second is provider._clients["k2"]


def test_openai_chat_single_key_one_client():
    provider = _ChatProbe(ProviderConfig(api_key="solo"))
    assert set(provider._clients) == {"solo"}
    assert provider._select_client() is provider._clients["solo"]
