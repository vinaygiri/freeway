"""Descriptor-driven provider for standard OpenAI-compatible chat endpoints.

Many free/free-tier providers speak vanilla OpenAI ``/chat/completions`` with
Bearer auth and need no per-provider request quirks. Rather than a bespoke
subclass each, they share this one class configured entirely from the provider
catalog (``provider_name`` + ``base_url``) with the default request policy.

Providers with real quirks (custom ``max_tokens`` field, header rewrites,
account-scoped URLs, native Anthropic transport) keep their own dedicated
adapter — this class is only for the standard case.
"""

from __future__ import annotations

from typing import Any

from providers.base import ProviderConfig
from providers.transports.openai_chat import (
    OpenAIChatRequestPolicy,
    OpenAIChatTransport,
    build_openai_chat_request_body,
)


class GenericOpenAIChatProvider(OpenAIChatTransport):
    """Standard OpenAI ``/chat/completions`` provider driven by catalog config."""

    def __init__(
        self, config: ProviderConfig, *, provider_name: str, base_url: str
    ) -> None:
        super().__init__(
            config,
            provider_name=provider_name,
            base_url=base_url,
            api_key=config.api_key,
        )
        self._policy = OpenAIChatRequestPolicy(provider_name=provider_name)

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        return build_openai_chat_request_body(
            request,
            thinking_enabled=self._is_thinking_enabled(request, thinking_enabled),
            policy=self._policy,
        )
