"""Tests for budget-based auto-fit tool trimming."""

from __future__ import annotations

from api.auto_fit import parse_keep_tools, trim_tools_to_budget
from api.models.anthropic import Tool


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
