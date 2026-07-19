"""Tests for budget-based auto-fit tool trimming."""

from __future__ import annotations

import json

from api.auto_fit import (
    _first_sentence,
    _strip_schema_descriptions,
    compress_tools_to_budget,
    parse_keep_tools,
    trim_messages_to_budget,
    trim_tools_to_budget,
)
from api.models.anthropic import (
    ContentBlockToolResult,
    ContentBlockToolUse,
    Message,
    Tool,
)


def _tool(name: str, size: int) -> Tool:
    return Tool(name=name, description="x" * size, input_schema={"type": "object"})


def _counter(messages, system, tools) -> int:
    """Deterministic token proxy: 1 token per 4 chars of tool description."""
    total = 0
    for t in tools or []:
        total += (len(t.description or "") // 4) + 1
    # small fixed cost for messages/system so base is nonzero
    total += 10 if messages else 0
    return total


def test_parse_keep_tools() -> None:
    assert parse_keep_tools("Bash, Read ,Edit") == frozenset({"Bash", "Read", "Edit"})


def test_no_trim_when_under_budget() -> None:
    tools = [_tool("Bash", 40), _tool("Workflow", 40)]
    kept = trim_tools_to_budget(
        messages=["m"],
        system=None,
        tools=tools,
        max_tokens=1000,
        keep_names=frozenset({"Bash"}),
        count_tokens=_counter,
    )
    assert kept is not None and [t.name for t in kept] == ["Bash", "Workflow"]


def test_drops_largest_nonessential_until_fit() -> None:
    tools = [
        _tool("Bash", 40),  # essential, ~11 tokens
        _tool("Workflow", 4000),  # ~1001 tokens
        _tool("DesignSync", 2000),  # ~501 tokens
        _tool("Read", 40),  # essential
    ]
    # base with all: 10 + 11 + 1001 + 501 + 11 = 1534; budget 600 -> must drop.
    kept = trim_tools_to_budget(
        messages=["m"],
        system=None,
        tools=tools,
        max_tokens=600,
        keep_names=frozenset({"Bash", "Read"}),
        count_tokens=_counter,
    )
    names = [t.name for t in (kept or [])]
    # Drops Workflow first (biggest). 1534-1001=533 <= 600 -> stops. DesignSync kept.
    assert "Workflow" not in names
    assert "DesignSync" in names
    assert {"Bash", "Read"} <= set(names)


def test_keeps_essentials_even_if_over_budget() -> None:
    tools = [_tool("Bash", 8000), _tool("Read", 8000), _tool("Workflow", 8000)]
    kept = trim_tools_to_budget(
        messages=["m"],
        system=None,
        tools=tools,
        max_tokens=100,  # impossible; essentials must survive
        keep_names=frozenset({"Bash", "Read"}),
        count_tokens=_counter,
    )
    names = {t.name for t in (kept or [])}
    assert names == {"Bash", "Read"}  # Workflow dropped, essentials kept


def test_none_when_all_dropped() -> None:
    tools = [_tool("Workflow", 8000), _tool("DesignSync", 8000)]
    kept = trim_tools_to_budget(
        messages=["m"],
        system=None,
        tools=tools,
        max_tokens=5,
        keep_names=frozenset(),  # nothing essential
        count_tokens=_counter,
    )
    assert kept is None


def test_noop_without_tools_or_budget() -> None:
    assert (
        trim_tools_to_budget(
            messages=["m"],
            system=None,
            tools=None,
            max_tokens=100,
            keep_names=frozenset(),
            count_tokens=_counter,
        )
        is None
    )
    tools = [_tool("Bash", 40)]
    kept = trim_tools_to_budget(
        messages=["m"],
        system=None,
        tools=tools,
        max_tokens=0,  # disabled
        keep_names=frozenset(),
        count_tokens=_counter,
    )
    assert kept is not None and [t.name for t in kept] == ["Bash"]


# ---- message backstop (trim_messages_to_budget) ----


def _mcounter(messages, system, tools) -> int:
    """~1 token per 4 chars of message + tool content."""
    total = 0
    for m in messages or []:
        content = getattr(m, "content", m)
        text = content if isinstance(content, str) else str(content)
        total += len(text) // 4 + 1
    for t in tools or []:
        total += (len(t.description or "") // 4) + 1
    return total


def _umsg(text: str) -> Message:
    return Message(role="user", content=text)


def _amsg(text: str) -> Message:
    return Message(role="assistant", content=text)


def test_messages_no_trim_when_under_budget() -> None:
    msgs = [_umsg("hi"), _amsg("hello")]
    kept = trim_messages_to_budget(
        messages=msgs, system=None, tools=None, max_tokens=1000, count_tokens=_mcounter
    )
    assert kept == msgs  # untouched


def test_messages_drop_oldest_until_fit_keeping_current() -> None:
    msgs = [_umsg("x" * 400), _amsg("y" * 400), _umsg("z" * 400), _umsg("now")]
    kept = trim_messages_to_budget(
        messages=msgs, system=None, tools=None, max_tokens=40, count_tokens=_mcounter
    )
    assert _mcounter(kept, None, None) <= 40
    assert kept[-1].content == "now"  # the current turn is always preserved
    assert len(kept) < len(msgs)


def test_messages_never_leave_orphan_tool_result() -> None:
    # A tool_use (assistant) + its tool_result (user) in the middle; trimming the
    # oldest must not leave the tool_result as the first message (would be invalid).
    tool_use = Message(
        role="assistant",
        content=[ContentBlockToolUse(type="tool_use", id="t1", name="Bash", input={})],
    )
    tool_result = Message(
        role="user",
        content=[
            ContentBlockToolResult(type="tool_result", tool_use_id="t1", content="out")
        ],
    )
    msgs = [_umsg("x" * 800), tool_use, tool_result, _umsg("current")]
    kept = trim_messages_to_budget(
        messages=msgs, system=None, tools=None, max_tokens=30, count_tokens=_mcounter
    )
    assert kept[0].role == "user"
    # first message must not lead with a tool_result block
    first = kept[0].content
    if isinstance(first, list) and first:
        assert getattr(first[0], "type", None) != "tool_result"
    assert kept[-1].content == "current"


def test_messages_noop_when_disabled_or_single() -> None:
    msgs = [_umsg("x" * 4000), _umsg("y" * 4000)]
    assert (
        trim_messages_to_budget(
            messages=msgs, system=None, tools=None, max_tokens=0, count_tokens=_mcounter
        )
        == msgs
    )
    one = [_umsg("x" * 4000)]
    assert (
        trim_messages_to_budget(
            messages=one, system=None, tools=None, max_tokens=5, count_tokens=_mcounter
        )
        == one  # never drop the only/current message
    )


# ---- tool-description compression (compress_tools_to_budget) — v2.6.0 ----


def _ctool(name: str, desc: str, schema: dict) -> Tool:
    return Tool(name=name, description=desc, input_schema=schema)


def _ccounter(messages, system, tools) -> int:
    """Mirror core get_token_count for tools: name + description + json(schema)."""
    total = 0
    for t in tools or []:
        blob = t.name + (t.description or "") + json.dumps(t.input_schema or {})
        total += len(blob) // 4 + 1
    total += 10 if messages else 0
    return total


def test_first_sentence() -> None:
    # v2.6.0
    assert _first_sentence("First sentence. Second one.") == "First sentence"
    assert _first_sentence("Line one\nLine two") == "Line one"
    assert _first_sentence("short") == "short"
    assert _first_sentence("") == ""
    assert _first_sentence("z" * 300) == "z" * 200  # capped at _MAX_TOOL_DESC_CHARS


def test_strip_schema_descriptions_recursive() -> None:
    # v2.6.0
    schema = {
        "type": "object",
        "description": "top-level prose",
        "properties": {
            "a": {"type": "string", "description": "param a prose"},
            "b": {
                "type": "array",
                "items": {"type": "object", "description": "nested"},
            },
        },
        "required": ["a"],
    }
    out = _strip_schema_descriptions(schema)
    assert "description" not in json.dumps(out)  # gone at every depth
    assert out["type"] == "object"
    assert out["required"] == ["a"]  # machine-relevant parts preserved
    assert out["properties"]["a"] == {"type": "string"}
    assert out["properties"]["b"]["items"] == {"type": "object"}


def test_strip_schema_keeps_property_named_description() -> None:
    # v2.6.0 regression: a tool parameter literally NAMED "description" (Agent,
    # Monitor, TaskCreate, ...) must survive. Dropping it while it stays in
    # "required" yields an invalid schema the provider rejects (HTTP 400).
    schema = {
        "type": "object",
        "description": "annotation prose to drop",
        "properties": {
            "description": {"type": "string", "description": "param's own prose"},
            "prompt": {"type": "string", "description": "more prose"},
        },
        "required": ["description", "prompt"],
    }
    out = _strip_schema_descriptions(schema)
    # the PROPERTY named "description" survives (still declared + required-valid)
    assert out["properties"]["description"] == {"type": "string"}
    assert out["required"] == ["description", "prompt"]
    assert set(out["properties"]) == {"description", "prompt"}
    # ...but every annotation prose value is gone
    assert "prose" not in json.dumps(out)


def test_compress_noop_when_under_budget() -> None:
    # v2.6.0
    tools = [_ctool("Bash", "d" * 40, {"type": "object"})]
    out, changed = compress_tools_to_budget(
        messages=["m"],
        system=None,
        tools=tools,
        max_tokens=10_000,
        keep_names=frozenset({"Bash"}),
        count_tokens=_ccounter,
    )
    assert changed is False
    assert out[0].description == "d" * 40  # untouched


def test_compress_level1_strips_schema_prose_keeps_descriptions() -> None:
    # v2.6.0 — Level 1 alone makes it fit: schema prose stripped, tool desc kept.
    big_schema = {
        "type": "object",
        "properties": {"x": {"type": "string", "description": "P" * 400}},
        "required": ["x"],
    }
    tools = [_ctool("Workflow", "T" * 40, big_schema)]
    before = _ccounter(["m"], None, tools)
    out, changed = compress_tools_to_budget(
        messages=["m"],
        system=None,
        tools=tools,
        max_tokens=before - 1,  # just over budget
        keep_names=frozenset(),
        count_tokens=_ccounter,
    )
    assert changed is True
    assert out[0].description == "T" * 40  # tool-level description preserved
    assert "description" not in json.dumps(out[0].input_schema)  # param prose gone
    assert out[0].input_schema is not None
    assert out[0].input_schema["required"] == ["x"]  # still a valid schema
    assert isinstance(out[0], Tool)


def test_compress_level2_shortens_only_nonkeep_tools() -> None:
    # v2.6.0 — Level 1 can't fit (descriptions dominate) -> Level 2 shortens the
    # non-keep tool's description while the keep-list tool keeps its full description.
    tools = [
        _ctool("Bash", "B" * 800, {"type": "object"}),  # keep-list
        _ctool("Workflow", "W" * 800, {"type": "object"}),  # non-essential
    ]
    out, changed = compress_tools_to_budget(
        messages=["m"],
        system=None,
        tools=tools,
        max_tokens=50,  # impossible for Level 1 -> forces Level 2 (best effort)
        keep_names=frozenset({"Bash"}),
        count_tokens=_ccounter,
    )
    assert changed is True
    assert len(out) == 2  # every tool still present
    by_name = {t.name: t for t in out}
    assert by_name["Bash"].description == "B" * 800  # keep-list keeps full prose
    assert by_name["Workflow"].description == "W" * 200  # non-keep shortened (capped)


def test_compress_noop_without_tools_or_budget() -> None:
    # v2.6.0
    out, changed = compress_tools_to_budget(
        messages=["m"],
        system=None,
        tools=None,
        max_tokens=100,
        keep_names=frozenset(),
        count_tokens=_ccounter,
    )
    assert out == [] and changed is False
    tools = [_ctool("Bash", "d" * 4000, {"type": "object"})]
    out, changed = compress_tools_to_budget(
        messages=["m"],
        system=None,
        tools=tools,
        max_tokens=0,  # disabled
        keep_names=frozenset(),
        count_tokens=_ccounter,
    )
    assert changed is False and out[0].description == "d" * 4000
