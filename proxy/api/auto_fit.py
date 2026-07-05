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


# Content-block types that may only appear as a reply to a preceding tool_use, so a
# message leading with one must never become the first message after trimming.
_TOOL_RESULT_TYPES = frozenset(
    {"tool_result", "web_search_tool_result", "web_fetch_tool_result"}
)


def _message_role(message: Any) -> str:
    role = getattr(message, "role", None)
    if role is None and isinstance(message, dict):
        role = message.get("role")
    return str(role or "")


def _leads_with_tool_result(message: Any) -> bool:
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    if not isinstance(content, list) or not content:
        return False
    first = content[0]
    block_type = getattr(first, "type", None)
    if block_type is None and isinstance(first, dict):
        block_type = first.get("type")
    return block_type in _TOOL_RESULT_TYPES


def trim_messages_to_budget(
    *,
    messages: Sequence[Any],
    system: Any,
    tools: Any,
    max_tokens: int,
    count_tokens: TokenCounter,
) -> list[Any]:
    """Drop the oldest conversation turns until the request fits ``max_tokens``.

    Last-resort backstop for when compaction hasn't kept the conversation small
    enough: preserves Anthropic validity by always keeping the final (current)
    message and never leaving a leading orphan ``tool_result`` (which requires a
    preceding ``tool_use``). Best effort — a single over-budget message is kept.
    """
    kept = list(messages)
    if max_tokens <= 0 or len(kept) <= 1:
        return kept
    if count_tokens(kept, system, tools) <= max_tokens:
        return kept

    while len(kept) > 1 and count_tokens(kept, system, tools) > max_tokens:
        kept.pop(0)
    # Repair the head: only drops more (never grows the request), so it still fits.
    while len(kept) > 1 and (
        _message_role(kept[0]) != "user" or _leads_with_tool_result(kept[0])
    ):
        kept.pop(0)
    return kept
