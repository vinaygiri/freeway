"""The :class:`Freeway` library facade.

Exposes Freeway's routing + cross-provider failover + multi-key rotation +
tool-schema compression as a plain Python object, driving the *same*
``MessagesHandler`` request path the proxy uses — no HTTP, no separate server.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from api.handlers.messages import MessagesHandler
from api.models.anthropic import MessagesRequest
from api.recommend import ModelScore, ProbeGetter
from api.recommend import recommend as _recommend
from api.recommend import suggest_chain as _suggest_chain
from config.provider_catalog import PROVIDER_CATALOG
from config.settings import Settings
from core.openai_chat_completions.input import convert_request_to_anthropic_payload
from providers.runtime.runtime import ProviderRuntime

_DEFAULT_MAX_TOKENS = 4096


class AllProvidersFailed(RuntimeError):
    """Raised when every provider in the chain failed and nothing was produced."""


@dataclass(slots=True)
class ToolCall:
    """A normalized tool/function call requested by the model."""

    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class Completion:
    """A buffered result. Failover is *observable*: ``served_model`` is the model
    that actually answered, ``was_fallback`` whether the primary was bypassed."""

    text: str
    tool_calls: list[ToolCall]
    stop_reason: str | None
    served_model: str | None
    was_fallback: bool
    input_tokens: int | None
    output_tokens: int | None
    raw: list[dict[str, Any]] = field(repr=False)


@dataclass(slots=True)
class StreamEvent:
    """A streaming event: ``type`` is ``text`` | ``tool_call`` | ``done``. The
    terminal ``done`` event carries the aggregated :class:`Completion`."""

    type: str
    text: str = ""
    tool_call: ToolCall | None = None
    completion: Completion | None = None


def _credential_env(provider_id: str) -> str:
    """Env var name that holds ``provider_id``'s key (from the provider catalog)."""
    entry = PROVIDER_CATALOG.get(provider_id)
    credential_env = getattr(entry, "credential_env", None)
    return credential_env or f"{provider_id.upper()}_API_KEY"


def _norm_model(ref: str | None) -> str:
    return (ref or "").rsplit("/", 1)[-1].lower()


class Freeway:
    """Resilient free-tier LLM routing as a library.

    >>> fw = Freeway(primary="gemini/models/gemini-2.5-flash",
    ...              fallbacks=["cerebras/gpt-oss-120b"],
    ...              keys={"gemini": "...", "cerebras": "..."})
    >>> c = fw.chat(messages=[{"role": "user", "content": "hi"}])
    >>> c.text, c.served_model, c.was_fallback

    Failover, multi-key rotation (pass a list for a provider), and tool-schema
    compression are applied automatically inside every call.
    """

    def __init__(
        self,
        primary: str | None = None,
        fallbacks: Sequence[str] | None = None,
        keys: Mapping[str, str | Sequence[str]] | None = None,
        *,
        auto_fit: bool | int = True,
        compress_tools: bool = True,
        auth_token: str = "",
    ) -> None:
        # Freeway is configured through the same Settings the proxy uses; explicit
        # args are applied to the process environment, then Settings is loaded so a
        # library call routes identically to the server. Omit args to use the
        # existing environment / ~/.freeway/.env (see :meth:`from_env`).
        if keys:
            for provider_id, value in keys.items():
                joined = (
                    ",".join(value) if isinstance(value, (list, tuple)) else str(value)
                )
                os.environ[_credential_env(provider_id)] = joined
        if primary is not None:
            os.environ["MODEL"] = primary
        if fallbacks is not None:
            os.environ["MODEL_FALLBACKS"] = ",".join(fallbacks)
        os.environ["ANTHROPIC_AUTH_TOKEN"] = auth_token
        if auto_fit is True:
            os.environ["AUTO_FIT_MAX_TOKENS"] = "0"
        elif auto_fit is False:
            os.environ["AUTO_FIT_MAX_TOKENS"] = "-1"
        else:
            os.environ["AUTO_FIT_MAX_TOKENS"] = str(int(auto_fit))
        os.environ["AUTO_FIT_COMPRESS_TOOLS"] = "true" if compress_tools else "false"

        self._settings = Settings()
        self._runtime = ProviderRuntime(self._settings)
        self._handler = MessagesHandler(self._settings, self._runtime.resolve_provider)
        self._default_model = primary or self._settings.model
        self._fallbacks = (
            list(fallbacks)
            if fallbacks is not None
            else [
                r.strip()
                for r in self._settings.model_fallbacks.split(",")
                if r.strip()
            ]
        )

    @classmethod
    def from_env(cls) -> Freeway:
        """Build from the existing environment / ``~/.freeway/.env`` (no overrides)."""
        return cls()

    def recommend(
        self,
        models: Sequence[str] | None = None,
        *,
        probe_getter: ProbeGetter | None = None,
        limit: int | None = None,
    ) -> list[ModelScore]:
        """Rank models best-first by live probe status x quality x context.

        ``models`` defaults to the configured primary + fallbacks. When available,
        live verification results from ``~/.freeway/model_probes.json`` sharpen the
        ranking (run the proxy's *Verify* to populate them).
        """
        return _recommend(
            self._candidate_refs(models),
            probe_getter=probe_getter or self._default_probe_getter(),
            limit=limit,
        )

    def suggest_chain(
        self,
        models: Sequence[str] | None = None,
        *,
        probe_getter: ProbeGetter | None = None,
        max_models: int = 4,
    ) -> list[str]:
        """Propose a provider-diversified fallback chain (feed it back as ``fallbacks``)."""
        return _suggest_chain(
            self._candidate_refs(models),
            probe_getter=probe_getter or self._default_probe_getter(),
            max_models=max_models,
        )

    def _candidate_refs(self, models: Sequence[str] | None) -> list[tuple[str, str]]:
        refs = (
            list(models)
            if models is not None
            else [self._default_model, *self._fallbacks]
        )
        out: list[tuple[str, str]] = []
        for ref in refs:
            provider, _, model = ref.partition("/")
            if provider and model:
                out.append((provider, model))
        return out

    @staticmethod
    def _default_probe_getter() -> ProbeGetter:
        """Best-effort live-verify lookup from the on-disk probe store (may be empty)."""
        from config.paths import config_dir_path
        from core.model_probe import PROBE_FILENAME, ProbeStore

        store = ProbeStore(config_dir_path() / PROBE_FILENAME)
        return store.get

    # -- public API -----------------------------------------------------------

    async def achat(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **extra: Any,
    ) -> Completion:
        """Run one request with failover + compression; return a buffered result."""
        request = self._build_request(
            messages,
            tools=tools,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            extra=extra,
        )
        events = await self._drain(await self._handler.create(request))
        return self._aggregate(events)

    async def astream(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **extra: Any,
    ) -> AsyncIterator[StreamEvent]:
        """Stream events as they arrive; the terminal ``done`` carries the Completion."""
        request = self._build_request(
            messages,
            tools=tools,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            extra=extra,
        )
        response = await self._handler.create(request)
        events: list[dict[str, Any]] = []
        async for event in self._iter_events(response):
            events.append(event)
            kind = event.get("type")
            if kind == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    yield StreamEvent(type="text", text=delta.get("text", ""))
        completion = self._aggregate(events)
        for call in completion.tool_calls:
            yield StreamEvent(type="tool_call", tool_call=call)
        yield StreamEvent(type="done", completion=completion)

    def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **extra: Any,
    ) -> Completion:
        """Synchronous :meth:`achat` (wraps it via ``asyncio.run``).

        Cannot be called from within a running event loop — use :meth:`achat` there.
        """
        return _run_sync(
            self.achat(
                messages,
                tools=tools,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                **extra,
            )
        )

    # -- internals ------------------------------------------------------------

    def _build_request(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None,
        model: str | None,
        max_tokens: int | None,
        temperature: float | None,
        extra: Mapping[str, Any],
    ) -> MessagesRequest:
        target = model or self._default_model
        openai_request: dict[str, Any] = {
            "model": target,
            "messages": list(messages),
            "stream": True,
        }
        if tools:
            openai_request["tools"] = list(tools)
        if max_tokens is not None:
            openai_request["max_tokens"] = max_tokens
        if temperature is not None:
            openai_request["temperature"] = temperature
        openai_request.update(extra)

        payload = dict(convert_request_to_anthropic_payload(openai_request))
        payload["model"] = target
        payload.setdefault("max_tokens", max_tokens or _DEFAULT_MAX_TOKENS)
        return MessagesRequest.model_validate(payload)

    @staticmethod
    async def _iter_events(response: Any) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed Anthropic SSE ``data:`` events from a streaming response."""
        body = getattr(response, "body_iterator", None)
        if body is None:
            return
        async for chunk in body:
            text = (
                chunk.decode() if isinstance(chunk, (bytes, bytearray)) else str(chunk)
            )
            for line in text.splitlines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue

    async def _drain(self, response: Any) -> list[dict[str, Any]]:
        return [event async for event in self._iter_events(response)]

    def _aggregate(self, events: list[dict[str, Any]]) -> Completion:
        text: list[str] = []
        tool_calls: list[ToolCall] = []
        stop_reason: str | None = None
        served: str | None = None
        input_tokens: int | None = None
        output_tokens: int | None = None
        error: dict[str, Any] | None = None
        pending_tool: dict[str, Any] | None = None
        pending_args: list[str] = []

        for event in events:
            kind = event.get("type")
            if kind == "message_start":
                message = event.get("message", {})
                served = message.get("model")
                input_tokens = (message.get("usage") or {}).get("input_tokens")
            elif kind == "content_block_start":
                block = event.get("content_block", {})
                if block.get("type") == "tool_use":
                    pending_tool = {"name": block.get("name", "")}
                    pending_args = []
            elif kind == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text.append(delta.get("text", ""))
                elif delta.get("type") == "input_json_delta":
                    pending_args.append(delta.get("partial_json", ""))
            elif kind == "content_block_stop":
                if pending_tool is not None:
                    try:
                        arguments = json.loads("".join(pending_args) or "{}")
                    except json.JSONDecodeError:
                        arguments = {}
                    tool_calls.append(ToolCall(pending_tool["name"], arguments))
                    pending_tool = None
            elif kind == "message_delta":
                delta = event.get("delta", {})
                if delta.get("stop_reason"):
                    stop_reason = delta["stop_reason"]
                output_tokens = (event.get("usage") or {}).get(
                    "output_tokens", output_tokens
                )
            elif kind == "error":
                error = event.get("error", {})

        joined = "".join(text)
        if error is not None and not joined and not tool_calls:
            raise AllProvidersFailed(error.get("message", "all providers failed"))

        was_fallback = served is not None and _norm_model(served) != _norm_model(
            self._default_model
        )
        return Completion(
            text=joined,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            served_model=served,
            was_fallback=was_fallback,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw=events,
        )


def _run_sync(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError(
        "Freeway.chat() cannot be called from within a running event loop; "
        "use `await Freeway.achat(...)` instead."
    )
