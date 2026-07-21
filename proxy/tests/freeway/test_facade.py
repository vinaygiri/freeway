"""Tests for the Freeway library facade (hermetic — no network)."""

from __future__ import annotations

import asyncio
import os

import pytest

from freeway import AllProvidersFailed, Completion, Freeway, ModelScore, ToolCall


@pytest.fixture(autouse=True)
def _isolate_env():
    """Freeway(...) writes routing config to os.environ; restore it after each test."""
    snapshot = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(snapshot)


def _fw() -> Freeway:
    return Freeway(
        primary="gemini/models/gemini-2.5-flash",
        fallbacks=["cerebras/gpt-oss-120b"],
        keys={"gemini": "k", "cerebras": "k2"},
    )


def test_config_writes_expected_env() -> None:
    # real provider refs — Settings validates MODEL against the provider catalog
    Freeway(
        primary="gemini/models/gemini-2.5-flash",
        fallbacks=["cerebras/gpt-oss-120b", "groq/llama-3.3-70b-versatile"],
        keys={"gemini": ["k1", "k2"], "cerebras": "solo"},
        auto_fit=8000,
        compress_tools=False,
    )
    assert os.environ["MODEL"] == "gemini/models/gemini-2.5-flash"
    assert (
        os.environ["MODEL_FALLBACKS"]
        == "cerebras/gpt-oss-120b,groq/llama-3.3-70b-versatile"
    )
    assert os.environ["GEMINI_API_KEY"] == "k1,k2"  # multi-key -> comma-joined
    assert os.environ["CEREBRAS_API_KEY"] == "solo"
    assert os.environ["AUTO_FIT_MAX_TOKENS"] == "8000"
    assert os.environ["AUTO_FIT_COMPRESS_TOOLS"] == "false"


def test_auto_fit_flag_variants() -> None:
    Freeway(primary="gemini/models/gemini-2.5-flash", auto_fit=True)
    assert os.environ["AUTO_FIT_MAX_TOKENS"] == "0"  # adaptive
    Freeway(primary="gemini/models/gemini-2.5-flash", auto_fit=False)
    assert os.environ["AUTO_FIT_MAX_TOKENS"] == "-1"  # disabled


def test_build_request_converts_openai_to_anthropic() -> None:
    fw = _fw()
    req = fw._build_request(
        [{"role": "user", "content": "hi"}],
        tools=None,
        model=None,
        max_tokens=16,
        temperature=0.2,
        extra={},
    )
    assert req.model == "gemini/models/gemini-2.5-flash"
    assert req.max_tokens == 16
    assert [m.role for m in req.messages] == ["user"]


def test_aggregate_text_stop_and_tokens() -> None:
    fw = _fw()
    events = [
        {
            "type": "message_start",
            "message": {
                "model": "models/gemini-2.5-flash",
                "usage": {"input_tokens": 10},
            },
        },
        {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "Hello "},
        },
        {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "world"},
        },
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"output_tokens": 3},
        },
        {"type": "message_stop"},
    ]
    c = fw._aggregate(events)
    assert isinstance(c, Completion)
    assert c.text == "Hello world"
    assert c.stop_reason == "end_turn"
    assert c.served_model == "models/gemini-2.5-flash"
    assert c.input_tokens == 10 and c.output_tokens == 3
    assert c.was_fallback is False  # served == primary


def test_aggregate_detects_fallback() -> None:
    fw = _fw()  # primary is gemini
    events = [
        {"type": "message_start", "message": {"model": "gpt-oss-120b", "usage": {}}},
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hi"}},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn"}},
    ]
    c = fw._aggregate(events)
    assert c.served_model == "gpt-oss-120b"
    assert c.was_fallback is True  # differs from configured primary


def test_aggregate_assembles_tool_call() -> None:
    fw = _fw()
    events = [
        {"type": "message_start", "message": {"model": "models/gemini-2.5-flash"}},
        {
            "type": "content_block_start",
            "content_block": {"type": "tool_use", "name": "Read"},
        },
        {
            "type": "content_block_delta",
            "delta": {"type": "input_json_delta", "partial_json": '{"file_path":'},
        },
        {
            "type": "content_block_delta",
            "delta": {"type": "input_json_delta", "partial_json": ' "/tmp/x"}'},
        },
        {"type": "content_block_stop"},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use"}},
    ]
    c = fw._aggregate(events)
    assert c.stop_reason == "tool_use"
    assert c.tool_calls == [ToolCall(name="Read", arguments={"file_path": "/tmp/x"})]


def test_aggregate_raises_on_error_event() -> None:
    fw = _fw()
    events = [
        {"type": "error", "error": {"type": "api_error", "message": "all failed"}}
    ]
    with pytest.raises(AllProvidersFailed, match="all failed"):
        fw._aggregate(events)


def test_recommend_scores_configured_chain() -> None:
    fw = _fw()  # primary gemini, fallback cerebras/gpt-oss-120b
    scores = fw.recommend(probe_getter=lambda _p, _m: {"kind": "live"})
    refs = {s.ref for s in scores}
    assert "gemini/models/gemini-2.5-flash" in refs
    assert "cerebras/gpt-oss-120b" in refs
    assert all(isinstance(s, ModelScore) for s in scores)


def test_suggest_chain_from_explicit_models_is_diversified() -> None:
    fw = _fw()
    chain = fw.suggest_chain(
        [
            "cerebras/gpt-oss-120b",
            "cerebras/zai-glm-4.7",
            "gemini/models/gemini-2.5-flash",
        ],
        probe_getter=lambda _p, _m: {"kind": "live"},
    )
    providers = [ref.split("/", 1)[0] for ref in chain]
    assert len(providers) == len(set(providers))  # one per provider
    assert set(providers) == {"cerebras", "gemini"}


def test_chat_inside_event_loop_raises() -> None:
    fw = _fw()

    async def run() -> None:
        with pytest.raises(RuntimeError, match="event loop"):
            fw.chat(messages=[{"role": "user", "content": "hi"}])

    asyncio.run(run())
