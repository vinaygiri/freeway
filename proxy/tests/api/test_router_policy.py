from __future__ import annotations

from api.data_governor import DataGovernor
from api.model_router import ResolvedModel
from api.quota_governor import QuotaGovernor
from api.router_policy import RoutingPolicy
from config.provider_quota import ProviderQuotaLimit
from core.circuit import CircuitBreaker
from core.health import HealthStore, Sample
from core.quota import QuotaTracker
from core.recent_requests import RecentRequestStore
from providers.model_listing import ProviderModelInfo


def _resolved(provider_id: str, model: str = "m") -> ResolvedModel:
    return ResolvedModel(
        original_model="x",
        provider_id=provider_id,
        provider_model=model,
        provider_model_ref=f"{provider_id}/{model}",
        thinking_enabled=False,
    )


def test_order_dedupes_and_preserves_configured_order_without_signals():
    policy = RoutingPolicy()
    a, b = _resolved("groq"), _resolved("cerebras")
    ordered = policy.order([a, b, _resolved("groq")])
    assert [r.provider_id for r in ordered] == ["groq", "cerebras"]


def test_order_puts_open_circuit_candidates_last():
    breaker = CircuitBreaker()
    for _ in range(3):
        breaker.record_failure("groq/m")  # open groq
    policy = RoutingPolicy(circuit_breaker=breaker)
    ordered = policy.order([_resolved("groq"), _resolved("cerebras")])
    assert [r.provider_id for r in ordered] == ["cerebras", "groq"]


def test_is_usable_false_when_quota_avoid():
    tracker = QuotaTracker()
    governor = QuotaGovernor(
        tracker, {"groq": ProviderQuotaLimit(provider_id="groq", rpm=1)}
    )
    tracker.record_request("groq")  # 1/1 rpm -> avoid
    policy = RoutingPolicy(quota_governor=governor)
    assert policy.is_usable(_resolved("groq")) is False
    assert policy.is_usable(_resolved("cerebras")) is True


def test_is_usable_false_when_health_dead():
    store = HealthStore()
    store.record("groq", Sample(code="ERR"))  # never up -> "Not Active"
    policy = RoutingPolicy(health_store=store)
    assert policy.is_usable(_resolved("groq")) is False


def test_order_deprioritizes_too_small_context_when_tokens_known():
    windows = {"small": 1000, "big": 200_000}

    def lookup(provider_id: str, model: str) -> ProviderModelInfo | None:
        cw = windows.get(model)
        return ProviderModelInfo(model_id=model, context_window=cw) if cw else None

    policy = RoutingPolicy(model_info_lookup=lookup)
    ordered = policy.order(
        [_resolved("open_router", "small"), _resolved("open_router", "big")],
        required_tokens=5000,
    )
    # "big" fits 5000 tokens; "small" is deprioritized to the back.
    assert [r.provider_model for r in ordered] == ["big", "small"]


def test_order_keeps_unknown_context_in_place():
    policy = RoutingPolicy(model_info_lookup=lambda _p, _m: None)
    ordered = policy.order(
        [_resolved("x", "a"), _resolved("x", "b")], required_tokens=999_999
    )
    assert [r.provider_model for r in ordered] == ["a", "b"]  # unknown -> not moved


def test_classify_returns_skip_reason():
    breaker = CircuitBreaker()
    for _ in range(3):
        breaker.record_failure("groq/m")
    assert (
        RoutingPolicy(circuit_breaker=breaker).classify(_resolved("groq")) == "circuit"
    )

    tracker = QuotaTracker()
    governor = QuotaGovernor(
        tracker, {"groq": ProviderQuotaLimit(provider_id="groq", rpm=1)}
    )
    tracker.record_request("groq")
    assert RoutingPolicy(quota_governor=governor).classify(_resolved("groq")) == "quota"

    store = HealthStore()
    store.record("groq", Sample(code="ERR"))
    assert RoutingPolicy(health_store=store).classify(_resolved("groq")) == "health"

    def lookup(_p: str, model: str) -> ProviderModelInfo:
        return ProviderModelInfo(model_id=model, context_window=1000)

    policy = RoutingPolicy(model_info_lookup=lookup)
    assert policy.classify(_resolved("open_router", "x"), required_tokens=5000) == (
        "context"
    )
    assert RoutingPolicy().classify(_resolved("groq")) is None


def test_record_request_captures_fallback_and_downgrade_reason():
    breaker = CircuitBreaker()
    for _ in range(3):
        breaker.record_failure(
            "groq/m"
        )  # primary groq circuit open -> reason "circuit"
    store = RecentRequestStore()
    policy = RoutingPolicy(circuit_breaker=breaker, recent_requests=store)
    policy.record_request(
        primary=_resolved("groq"),
        served=_resolved("cerebras"),
        gateway_model="claude-sonnet-4",
        input_tokens=10,
        candidates_tried=2,
        outcome="routed",
    )
    record = store.snapshot()[0]
    assert record["was_fallback"] is True
    assert record["downgrade_reason"] == "circuit"
    assert record["provider_id"] == "cerebras"
    assert record["gateway_model"] == "claude-sonnet-4"


def test_record_request_is_noop_without_store():
    # No store wired -> must not raise.
    RoutingPolicy().record_request(
        primary=_resolved("groq"),
        served=_resolved("groq"),
        gateway_model="m",
        input_tokens=1,
        candidates_tried=1,
        outcome="routed",
    )


def test_order_hard_drops_policy_violating_candidates():
    policy = RoutingPolicy(data_governor=DataGovernor(require_local_only=True))
    ordered = policy.order([_resolved("nvidia_nim"), _resolved("ollama")])
    assert [r.provider_id for r in ordered] == ["ollama"]  # non-local dropped entirely


def test_order_empty_when_all_candidates_violate_policy():
    policy = RoutingPolicy(data_governor=DataGovernor(require_local_only=True))
    assert policy.order([_resolved("nvidia_nim"), _resolved("groq")]) == []


def test_classify_reports_policy_reason():
    policy = RoutingPolicy(data_governor=DataGovernor(require_local_only=True))
    assert policy.classify(_resolved("nvidia_nim")) == "policy:local_only"


def test_record_failure_and_success_drive_circuit():
    breaker = CircuitBreaker()
    policy = RoutingPolicy(circuit_breaker=breaker)
    r = _resolved("groq")
    for _ in range(3):
        policy.record_failure(r)
    assert breaker.state_of("groq/m") == "open"
    policy.record_success(r)
    assert breaker.state_of("groq/m") == "closed"
