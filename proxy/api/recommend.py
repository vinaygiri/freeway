"""Live-verified model recommendation.

Ranks models by combining three signals — **live probe status** (does it actually
work right now), **static quality tier**, and **context size** — and can propose a
provider-diversified fallback chain. Deliberately *not* a static "best models" list:
scores reflect current probe results, so a recommendation never goes stale.

Lives in ``api`` (not ``core``) because it reads ``config.model_quality``; the scoring
itself is pure and side-effect free.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

from config.model_quality import MODEL_QUALITY, context_tokens_for

# How much a model's *current* liveness counts (does it work right now?).
_LIVENESS_WEIGHT: dict[str, float] = {
    "live": 1.0,  # verified working
    "unverified": 0.6,  # not probed yet — optimistic, but below a proven live model
    "rate_limited": 0.35,  # temporary
    "overloaded": 0.30,  # temporary
    "unavailable": 0.0,
    "down": 0.0,
}
# Quality by SWE-bench tier (see config/model_quality.py for the scale).
_TIER_WEIGHT: dict[str, float] = {
    "S+": 1.0,
    "S": 0.9,
    "A+": 0.8,
    "A": 0.7,
    "A-": 0.6,
    "B+": 0.45,
    "B": 0.3,
    "C": 0.15,
}
_UNKNOWN_TIER_WEIGHT = 0.4
_FULL_CONTEXT_TOKENS = 131_072  # 128k earns full context credit

_W_LIVENESS, _W_QUALITY, _W_CONTEXT = 0.50, 0.35, 0.15
_EXCLUDED_LIVENESS = frozenset({"down", "unavailable"})

# Non-chat models a provider also exposes (image/video/audio/embedding/etc.).
# Recommending one as a *coding* fallback is nonsense, so they're excluded — a
# heuristic on the model id, since discovery doesn't tag modality.
_NON_CHAT_MARKERS = (
    "veo",
    "imagen",
    "lyria",
    "nano-banana",
    "dall-e",
    "sora",
    "whisper",
    "embed",
    "embedding",
    "rerank",
    "moderation",
    "-tts",
    "text-to-speech",
    "-transcribe",
    "image-generation",
)

ProbeGetter = Callable[[str, str], Mapping[str, object] | None]


def _is_chat_candidate(model_id: str) -> bool:
    """Heuristic: exclude obvious non-text-generation models from recommendations."""
    low = model_id.lower()
    return not any(marker in low for marker in _NON_CHAT_MARKERS)


@dataclass(frozen=True, slots=True)
class ModelScore:
    """A scored model. ``reasons`` explains the score (for UI / debugging)."""

    provider_id: str
    model_id: str
    ref: str
    score: float
    liveness: str
    tier: str | None
    context_tokens: int | None
    reasons: list[str] = field(default_factory=list)


def _liveness_of(probe: Mapping[str, object] | None) -> str:
    if not probe:
        return "unverified"
    kind = str(probe.get("kind") or probe.get("status") or "unverified")
    return kind if kind in _LIVENESS_WEIGHT else "unverified"


def score_model(
    provider_id: str,
    model_id: str,
    *,
    probe: Mapping[str, object] | None = None,
) -> ModelScore:
    """Score one model (0-100) from live status x quality tier x context."""
    liveness = _liveness_of(probe)
    quality = MODEL_QUALITY.get(model_id) or {}
    tier = quality.get("tier")
    context_tokens = context_tokens_for(model_id)

    live_w = _LIVENESS_WEIGHT.get(liveness, _LIVENESS_WEIGHT["unverified"])
    tier_w = _TIER_WEIGHT.get(tier or "", _UNKNOWN_TIER_WEIGHT)
    context_w = (
        min(1.0, context_tokens / _FULL_CONTEXT_TOKENS) if context_tokens else 0.3
    )
    score = round(
        100 * (_W_LIVENESS * live_w + _W_QUALITY * tier_w + _W_CONTEXT * context_w), 1
    )
    reasons = [
        f"live:{liveness}",
        f"tier:{tier or '?'}",
        f"ctx:{context_tokens // 1000 if context_tokens else '?'}k",
    ]
    return ModelScore(
        provider_id=provider_id,
        model_id=model_id,
        ref=f"{provider_id}/{model_id}",
        score=score,
        liveness=liveness,
        tier=tier,
        context_tokens=context_tokens,
        reasons=reasons,
    )


def recommend(
    models: Iterable[tuple[str, str]],
    *,
    probe_getter: ProbeGetter | None = None,
    limit: int | None = None,
) -> list[ModelScore]:
    """Return ``(provider_id, model_id)`` pairs scored and ranked best-first.

    Non-chat models (image/video/audio/embedding) and verified-down / unavailable
    models are excluded (recommending either as a coding fallback is worse than
    useless). Unprobed models are kept (optimistic) but rank below verified-live ones.
    """
    get = probe_getter or (lambda _p, _m: None)
    chat = [(p, m) for p, m in models if _is_chat_candidate(m)]
    scored = [score_model(p, m, probe=get(p, m)) for p, m in chat]
    scored = [s for s in scored if s.liveness not in _EXCLUDED_LIVENESS]
    scored.sort(key=lambda s: (s.score, s.ref), reverse=True)
    return scored[:limit] if limit else scored


def suggest_chain(
    models: Iterable[tuple[str, str]],
    *,
    probe_getter: ProbeGetter | None = None,
    max_models: int = 4,
) -> list[str]:
    """Propose a resilient fallback chain: the best model from each of the top
    providers (one per provider), so exhausting one provider's quota falls over to
    a *different* provider rather than a sibling model on the same limited account.
    """
    chain: list[str] = []
    seen_providers: set[str] = set()
    for model in recommend(models, probe_getter=probe_getter):
        if model.provider_id in seen_providers:
            continue
        seen_providers.add(model.provider_id)
        chain.append(model.ref)
        if len(chain) >= max_models:
            break
    return chain
