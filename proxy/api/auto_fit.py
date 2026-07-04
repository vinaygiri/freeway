"""Auto-fit an over-budget request by trimming tool schemas to a token budget.

Editor clients attach every tool's full JSON schema to every request. On a small
free-tier per-minute token budget, that baseline alone can exceed the limit and
the provider rejects the request (HTTP 413) before any real work happens.

When ``AUTO_FIT_MAX_TOKENS`` is set, we estimate the request's token count and,
if it's over budget, drop the largest *non-essential* tools (largest first)
until it fits — keeping the core coding tools listed in ``AUTO_FIT_KEEP_TOOLS``.
Best-effort: if even the kept tools plus system/messages exceed the budget, we
return the kept set (we won't drop essentials); the caller logs that case.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol


class _NamedTool(Protocol):
    name: str


# Matches ``core.anthropic.get_token_count(messages, system, tools) -> int``.
TokenCounter = Callable[[Any, Any, Any], int]


def parse_keep_tools(spec: str) -> frozenset[str]:
    """Parse a comma-separated keep-list into a set of exact tool names."""
    return frozenset(name.strip() for name in spec.split(",") if name.strip())


def trim_tools_to_budget[T: _NamedTool](
    *,
    messages: Any,
    system: Any,
    tools: Sequence[T] | None,
    max_tokens: int,
    keep_names: frozenset[str],
    count_tokens: TokenCounter,
) -> list[T] | None:
    """Return ``tools`` trimmed so the request fits ``max_tokens`` (best effort).

    Returns the input unchanged (as a list) when already within budget or no
    trimming applies, and ``None`` when the result is empty.
    """
    if not tools or max_tokens <= 0:
        return list(tools) if tools else None

    kept: list[T] = list(tools)
    if count_tokens(messages, system, kept) <= max_tokens:
        return kept

    # Drop the biggest non-essential tools first until we fit (or run out).
    droppable = sorted(
        (tool for tool in tools if tool.name not in keep_names),
        key=lambda tool: count_tokens([], None, [tool]),
        reverse=True,
    )
    for tool in droppable:
        if count_tokens(messages, system, kept) <= max_tokens:
            break
        kept.remove(tool)

    return kept or None
