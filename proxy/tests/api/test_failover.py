from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.model_router import ModelRouter, ResolvedModel, RoutedMessagesRequest
from api.models.anthropic import MessagesRequest
from api.provider_execution import ProviderExecutionService
from api.quota_governor import QuotaGovernor
from api.router_policy import RoutingPolicy
from config.provider_quota import ProviderQuotaLimit
from config.settings import Settings
from core.circuit import CircuitBreaker
from core.quota import QuotaTracker
from providers.base import BaseProvider
from providers.exceptions import APIError, AuthenticationError, ProviderError


class _FakeProvider(BaseProvider):
    def __init__(self) -> None:
        pass

    async def cleanup(self) -> None:
        return None

    async def list_model_ids(self) -> frozenset[str]:
        return frozenset()

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        yield "data: ok\n\n"


def _routed(provider_id: str, model: str = "m") -> RoutedMessagesRequest:
    resolved = ResolvedModel(
        original_model="x",
        provider_id=provider_id,
        provider_model=model,
        provider_model_ref=f"{provider_id}/{model}",
        thinking_enabled=False,
    )
    request = MessagesRequest.model_validate(
        {"model": model, "messages": [{"role": "user", "content": "hi"}]}
    )
    return RoutedMessagesRequest(request=request, resolved=resolved)


def _fallback(provider_id: str, model: str = "m") -> ResolvedModel:
    return _routed(provider_id, model).resolved


def _service(getter, policy: RoutingPolicy) -> ProviderExecutionService:
    return ProviderExecutionService(Settings(), getter, routing_policy=policy)


def _getter(raising: dict[str, Exception], calls: list[str]):
    provider = _FakeProvider()

    def getter(provider_id: str) -> BaseProvider:
        calls.append(provider_id)
        if provider_id in raising:
            raise raising[provider_id]
        return provider

    return getter


def _run(service, primary, fallbacks):
    # stream_with_failover is async and peeks the opening chunk before returning;
    # run it to completion so candidate resolution + circuit bookkeeping happen.
    return asyncio.run(
        service.stream_with_failover(
            primary,
            fallbacks,
            wire_api="messages",
            raw_log_label="X",
            raw_log_payload={},
        )
    )


def test_primary_success_returns_without_touching_fallback():
    calls: list[str] = []
    service = _service(_getter({}, calls), RoutingPolicy())
    result = _run(service, _routed("groq"), [_fallback("cerebras")])
    assert result is not None
    assert calls == ["groq"]  # fallback never resolved


def test_fails_over_to_next_on_preflight_error():
    calls: list[str] = []
    breaker = CircuitBreaker()
    service = _service(
        _getter({"groq": APIError("down", status_code=503)}, calls),
        RoutingPolicy(circuit_breaker=breaker),
    )
    result = _run(service, _routed("groq"), [_fallback("cerebras")])
    assert result is not None
    assert calls == ["groq", "cerebras"]
    assert breaker.snapshot()["groq/m"]["consecutive_failures"] == 1
    assert breaker.state_of("cerebras/m") == "closed"  # success recorded


def test_auth_error_poison_skips_remaining_models_of_provider():
    calls: list[str] = []
    service = _service(
        _getter({"groq": AuthenticationError("no key")}, calls),
        RoutingPolicy(),
    )
    # groq primary + a second groq model + a cerebras fallback
    result = _run(
        service,
        _routed("groq", "m1"),
        [_fallback("groq", "m2"), _fallback("cerebras", "m3")],
    )
    assert result is not None
    assert calls == ["groq", "cerebras"]  # groq/m2 skipped after auth failure


def test_failover_walks_entire_chain_beyond_three():
    # A user with many fallback providers must have ALL of them tried, not an
    # arbitrary 3 — the whole point of "never stops". First four fail, the fifth
    # (a fresh provider) succeeds; it must be reached.
    calls: list[str] = []
    service = _service(
        _getter(
            {
                "p1": APIError("a", status_code=503),
                "p2": APIError("b", status_code=503),
                "p3": APIError("c", status_code=503),
                "p4": APIError("d", status_code=503),
            },
            calls,
        ),
        RoutingPolicy(),
    )
    result = _run(
        service,
        _routed("p1"),
        [_fallback("p2"), _fallback("p3"), _fallback("p4"), _fallback("p5")],
    )
    assert result is not None  # reached and committed the 5th candidate
    assert calls == ["p1", "p2", "p3", "p4", "p5"]  # every candidate tried


def test_all_candidates_fail_raises_provider_error():
    calls: list[str] = []
    service = _service(
        _getter(
            {
                "groq": APIError("a", status_code=503),
                "cerebras": APIError("b", status_code=500),
            },
            calls,
        ),
        RoutingPolicy(),
    )
    with pytest.raises(ProviderError):
        _run(service, _routed("groq"), [_fallback("cerebras")])


def test_quota_avoid_reorders_so_healthy_provider_is_tried_first():
    tracker = QuotaTracker()
    governor = QuotaGovernor(
        tracker, {"groq": ProviderQuotaLimit(provider_id="groq", rpm=1)}
    )
    tracker.record_request("groq")  # groq -> avoid
    calls: list[str] = []
    service = _service(_getter({}, calls), RoutingPolicy(quota_governor=governor))
    result = _run(service, _routed("groq"), [_fallback("cerebras")])
    assert result is not None
    assert calls == ["cerebras"]  # healthy fallback tried first, groq skipped


def test_open_circuit_primary_is_skipped():
    breaker = CircuitBreaker()
    for _ in range(3):
        breaker.record_failure("groq/m")  # open groq
    calls: list[str] = []
    service = _service(_getter({}, calls), RoutingPolicy(circuit_breaker=breaker))
    result = _run(service, _routed("groq"), [_fallback("cerebras")])
    assert result is not None
    assert calls == ["cerebras"]


def test_resolve_fallback_candidates_filters_invalid():
    settings = Settings()
    settings.model_fallbacks = "groq/llama-3.3, cerebras/gpt-oss, bogus, notaprovider/x"
    candidates = ModelRouter(settings).resolve_fallback_candidates()
    assert [c.provider_id for c in candidates] == ["groq", "cerebras"]


class _ChunkProvider(BaseProvider):
    """Fake provider that yields a fixed list of SSE chunks."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    async def cleanup(self) -> None:
        return None

    async def list_model_ids(self) -> frozenset[str]:
        return frozenset()

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk


_CONTENT = 'event: content_block_start\ndata: {"type":"content_block_start"}\n\n'


def _chunk_getter(by_provider: dict[str, list[str]], calls: list[str]):
    def getter(provider_id: str) -> BaseProvider:
        calls.append(provider_id)
        return _ChunkProvider(by_provider[provider_id])

    return getter


def _collect(service, primary, fallbacks) -> list[str]:
    async def run() -> list[str]:
        it = await service.stream_with_failover(
            primary,
            fallbacks,
            wire_api="messages",
            raw_log_label="X",
            raw_log_payload={},
        )
        return [chunk async for chunk in it]

    return asyncio.run(run())


def test_peek_fails_over_on_pre_content_error():
    calls: list[str] = []
    breaker = CircuitBreaker()
    err = 'event: error\ndata: {"type":"error","error":{"type":"rate_limit_error","message":"429"}}\n\n'
    service = _service(
        _chunk_getter({"groq": [err], "cerebras": [_CONTENT, "data: hi\n\n"]}, calls),
        RoutingPolicy(circuit_breaker=breaker),
    )
    out = _collect(service, _routed("groq"), [_fallback("cerebras")])
    assert calls == ["groq", "cerebras"]  # groq's connect error triggered failover
    assert _CONTENT in out  # served content came from cerebras
    assert breaker.snapshot()["groq/m"]["consecutive_failures"] == 1


def test_peek_commits_on_content_without_touching_fallback():
    calls: list[str] = []
    service = _service(
        _chunk_getter(
            {"groq": [_CONTENT, "data: hi\n\n"], "cerebras": [_CONTENT]}, calls
        ),
        RoutingPolicy(),
    )
    out = _collect(service, _routed("groq"), [_fallback("cerebras")])
    assert calls == ["groq"]  # committed on groq, fallback never resolved
    assert out == [_CONTENT, "data: hi\n\n"]


def test_peek_auth_error_blocks_remaining_models_of_provider():
    calls: list[str] = []
    auth = 'event: error\ndata: {"type":"error","error":{"type":"authentication_error","message":"bad key"}}\n\n'
    service = _service(
        _chunk_getter({"groq": [auth], "cerebras": [_CONTENT]}, calls),
        RoutingPolicy(),
    )
    out = _collect(
        service,
        _routed("groq", "m1"),
        [_fallback("groq", "m2"), _fallback("cerebras", "m3")],
    )
    assert calls == ["groq", "cerebras"]  # groq/m2 skipped after auth error
    assert _CONTENT in out


def test_admin_router_endpoint_reports_circuits():
    app = create_app(lifespan_enabled=False)
    breaker = CircuitBreaker()
    breaker.record_failure("groq/m")
    app.state.circuit_breaker = breaker
    with TestClient(app, client=("127.0.0.1", 50000)) as local:
        response = local.get("/admin/api/router")
    assert response.status_code == 200
    assert "groq/m" in response.json()["circuits"]
