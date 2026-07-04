"""OpenAI-compatible chat transport base."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
from openai import AsyncOpenAI

from core.anthropic.streaming import AnthropicStreamLedger
from providers.base import BaseProvider, ProviderConfig
from providers.error_mapping import (
    extract_provider_error_detail,
    map_error,
    user_visible_message_for_mapped_provider_error,
)
from providers.key_pool import KeyPool
from providers.model_listing import extract_openai_model_ids
from providers.rate_limit import GlobalRateLimiter

from .stream import OpenAIChatStreamAdapter


class OpenAIChatTransport(BaseProvider):
    """Base for OpenAI-compatible ``/chat/completions`` adapters."""

    def __init__(
        self,
        config: ProviderConfig,
        *,
        provider_name: str,
        base_url: str,
        api_key: str,
    ):
        super().__init__(config)
        self._provider_name = provider_name
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._proxy = config.proxy
        self._timeout = httpx.Timeout(
            config.http_read_timeout,
            connect=config.http_connect_timeout,
            read=config.http_read_timeout,
            write=config.http_write_timeout,
        )
        self._global_rate_limiter = GlobalRateLimiter.get_scoped_instance(
            provider_name.lower(),
            rate_limit=config.rate_limit,
            rate_window=config.rate_window,
            max_concurrency=config.max_concurrency,
        )
        # One client per key (the key is baked into AsyncOpenAI at construction),
        # selected per request — avoids mutating a shared client across concurrent
        # streams. A single configured key yields a single client, as before.
        self._key_pool = KeyPool(config.api_keys)
        pool_keys = self._key_pool.keys() or [self._api_key]
        self._clients: dict[str, AsyncOpenAI] = {
            key: self._build_openai_client(key) for key in pool_keys
        }
        self._client = self._clients[pool_keys[0]]

    def _build_openai_client(self, api_key: str) -> AsyncOpenAI:
        http_client = None
        if self._proxy:
            http_client = httpx.AsyncClient(proxy=self._proxy, timeout=self._timeout)
        return AsyncOpenAI(
            api_key=api_key,
            base_url=self._base_url,
            max_retries=0,
            timeout=self._timeout,
            http_client=http_client,
        )

    def _select_client(self) -> AsyncOpenAI:
        """Return the client for the next pooled key (default client if unknown)."""
        return self._clients.get(self._key_pool.select(), self._client)

    async def cleanup(self) -> None:
        """Release HTTP client resources for every pooled client."""
        clients = list(getattr(self, "_clients", {}).values())
        client = getattr(self, "_client", None)
        if client is not None and client not in clients:
            clients.append(client)
        for pooled in clients:
            await pooled.close()

    async def list_model_ids(self) -> frozenset[str]:
        """Return model ids from the provider's OpenAI-compatible models endpoint."""
        payload = await self._client.models.list()
        return extract_openai_model_ids(payload, provider_name=self._provider_name)

    @abstractmethod
    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        """Build request body. Must be implemented by subclasses."""

    def _handle_extra_reasoning(
        self, delta: Any, ledger: AnthropicStreamLedger, *, thinking_enabled: bool
    ) -> Iterator[str]:
        """Hook for provider-specific reasoning."""
        return iter(())

    def _get_retry_request_body(self, error: Exception, body: dict) -> dict | None:
        """Return a modified request body for one retry, or None."""
        return None

    def _prepare_create_body(self, body: dict[str, Any]) -> dict[str, Any]:
        """Return the body passed to the upstream OpenAI-compatible client."""
        return body

    def _record_tool_call_extra_content(
        self, tool_call_id: str, extra_content: dict[str, Any]
    ) -> None:
        """Hook for providers that must replay OpenAI tool-call metadata later."""

    def _tool_argument_aliases(self, body: dict[str, Any]) -> dict[str, dict[str, str]]:
        """Return provider-specific per-tool argument aliases for this request."""
        return {}

    def _anthropic_usage_fields(self, usage_info: Any) -> dict[str, int]:
        """Return provider-specific Anthropic usage fields for final SSE usage."""
        return {}

    async def _create_stream(self, body: dict) -> tuple[Any, dict]:
        """Create a streaming chat completion, optionally retrying once."""
        client = self._select_client()
        try:
            create_body = self._prepare_create_body(body)
            stream = await self._global_rate_limiter.execute_with_retry(
                client.chat.completions.create, **create_body, stream=True
            )
            return stream, body
        except Exception as error:
            retry_body = self._get_retry_request_body(error, body)
            if retry_body is None:
                raise

            create_retry_body = self._prepare_create_body(retry_body)
            stream = await self._global_rate_limiter.execute_with_retry(
                client.chat.completions.create, **create_retry_body, stream=True
            )
            return stream, retry_body

    def _openai_error_message(self, error: Exception, request_id: str | None) -> str:
        mapped_error = map_error(error, rate_limiter=self._global_rate_limiter)
        return user_visible_message_for_mapped_provider_error(
            mapped_error,
            provider_name=self._provider_name,
            read_timeout_s=self._config.http_read_timeout,
            detail=extract_provider_error_detail(error),
            request_id=request_id,
        )

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        """Stream response in Anthropic SSE format."""
        adapter = OpenAIChatStreamAdapter(
            self,
            request=request,
            input_tokens=input_tokens,
            request_id=request_id,
            thinking_enabled=thinking_enabled,
        )
        async for event in adapter.run():
            yield event
