"""Tests for live-verified model recommendation."""

from __future__ import annotations

from api.recommend import ModelScore, recommend, score_model, suggest_chain


def _probe(kind: str) -> dict[str, str]:
    return {"kind": kind}


def test_live_model_outscores_identical_unverified() -> None:
    # Same model id; the one with a live probe must rank higher than an unprobed one.
    live = score_model("cerebras", "gpt-oss-120b", probe=_probe("live"))
    unverified = score_model("cerebras", "gpt-oss-120b", probe=None)
    assert live.score > unverified.score
    assert live.liveness == "live"
    assert unverified.liveness == "unverified"


def test_down_and_unavailable_excluded_from_recommendations() -> None:
    def getter(_p: str, model_id: str):
        return {"gpt-oss-120b": _probe("live"), "dead-model": _probe("down")}.get(
            model_id
        )

    ranked = recommend(
        [("cerebras", "gpt-oss-120b"), ("cerebras", "dead-model")],
        probe_getter=getter,
    )
    refs = [m.ref for m in ranked]
    assert "cerebras/gpt-oss-120b" in refs
    assert "cerebras/dead-model" not in refs  # verified-down never recommended


def test_ranked_best_first() -> None:
    ranked = recommend(
        [("a", "m1"), ("b", "m2"), ("c", "m3")],
        probe_getter=lambda _p, m: (
            _probe("live") if m == "m2" else _probe("rate_limited")
        ),
    )
    assert all(isinstance(m, ModelScore) for m in ranked)
    assert ranked[0].model_id == "m2"  # the only live one leads
    assert [m.score for m in ranked] == sorted((m.score for m in ranked), reverse=True)


def test_suggest_chain_is_provider_diversified() -> None:
    # Two live models on the same provider + one on another: the chain must not
    # stack two from one provider before covering the second provider.
    models = [
        ("cerebras", "gpt-oss-120b"),
        ("cerebras", "zai-glm-4.7"),
        ("gemini", "models/gemini-2.5-flash"),
    ]
    chain = suggest_chain(
        models, probe_getter=lambda _p, _m: _probe("live"), max_models=4
    )
    providers = [ref.split("/", 1)[0] for ref in chain]
    assert len(providers) == len(set(providers))  # one model per provider
    assert set(providers) == {"cerebras", "gemini"}


def test_suggest_chain_respects_max_models() -> None:
    models = [(f"p{i}", f"m{i}") for i in range(6)]
    chain = suggest_chain(
        models, probe_getter=lambda _p, _m: _probe("live"), max_models=3
    )
    assert len(chain) == 3


def test_non_chat_models_excluded() -> None:
    # image/video/audio/embedding models must never be recommended as coding fallbacks.
    models = [
        ("gemini", "models/gemini-2.5-flash"),
        ("gemini", "models/veo-3.1-generate-preview"),  # video
        ("gemini", "models/imagen-4.0"),  # image
        ("gemini", "models/text-embedding-004"),  # embedding
        ("openai", "whisper-1"),  # audio
    ]
    refs = {
        m.ref for m in recommend(models, probe_getter=lambda _p, _m: _probe("live"))
    }
    assert "gemini/models/gemini-2.5-flash" in refs
    assert not any(
        bad in " ".join(refs) for bad in ("veo", "imagen", "embedding", "whisper")
    )


def test_suggest_chain_skips_non_chat_for_provider_slot() -> None:
    # A provider whose only "live" models are media must not contribute a media model.
    models = [
        ("cerebras", "gpt-oss-120b"),
        ("gemini", "models/veo-3.1-generate-preview"),
        ("gemini", "models/gemini-2.5-flash"),
    ]
    chain = suggest_chain(models, probe_getter=lambda _p, _m: _probe("live"))
    assert "gemini/models/gemini-2.5-flash" in chain
    assert not any("veo" in ref for ref in chain)


def test_score_has_explainable_reasons() -> None:
    score = score_model("cerebras", "gpt-oss-120b", probe=_probe("live"))
    joined = " ".join(score.reasons)
    assert "live:live" in joined
    assert "tier:" in joined and "ctx:" in joined
