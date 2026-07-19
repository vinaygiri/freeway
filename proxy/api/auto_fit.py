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

from api.models.anthropic import Tool


class _NamedTool(Protocol):
    name: str


# Matches ``core.anthropic.get_token_count(messages, system, tools) -> int``.
TokenCounter = Callable[[Any, Any, Any], int]


def parse_keep_tools(spec: str) -> frozenset[str]:
    """Parse a comma-separated keep-list into a set of exact tool names."""
    return frozenset(name.strip() for name in spec.split(",") if name.strip())


# Max length of a shortened (first-sentence) tool description, in characters.
_MAX_TOOL_DESC_CHARS = 200


# JSON-Schema keys whose direct children are *named subschemas* (property names,
# not annotations). Their keys must be preserved — only their values are scrubbed —
# so a tool parameter literally named "description" survives (e.g. Agent/TaskCreate).
_SCHEMA_NAMED_MAPS = frozenset(
    {"properties", "$defs", "definitions", "patternProperties"}
)


def _strip_schema_descriptions(schema: Any) -> Any:
    """Return a copy of a JSON-schema value with annotation ``description`` prose
    removed, keeping the machine-relevant parts a provider needs (``type``,
    ``enum``, ``required``, ``properties``, ``items``).

    A ``description`` that is a *property name* (a key under ``properties``/``$defs``
    /``definitions``/``patternProperties``) is a real tool parameter and is kept —
    only string ``description`` *annotations* on a schema node are dropped. Removing
    the property while it stays in ``required`` would make the schema invalid and the
    provider reject the request.
    """
    if isinstance(schema, dict):
        out: dict[str, Any] = {}
        for key, value in schema.items():
            if key == "description" and isinstance(value, str):
                continue  # annotation prose — drop
            if key in _SCHEMA_NAMED_MAPS and isinstance(value, dict):
                out[key] = {
                    name: _strip_schema_descriptions(subschema)
                    for name, subschema in value.items()
                }
            else:
                out[key] = _strip_schema_descriptions(value)
        return out
    if isinstance(schema, list):
        return [_strip_schema_descriptions(item) for item in schema]
    return schema


def _first_sentence(text: str) -> str:
    """Reduce a tool description to its first sentence, capped in length.

    The model still learns what the tool does (name + one line) without the
    multi-paragraph usage prose that dominates the token cost.
    """
    line = text.strip().split("\n", 1)[0].strip()
    head = line.split(". ", 1)[0].strip()
    return (head or line)[:_MAX_TOOL_DESC_CHARS].strip()


def _compress_tool(tool: Tool, *, shorten_desc: bool) -> Tool:
    """Return a copy of ``tool`` with schema prose stripped and (optionally) a
    first-sentence description. Preserves every other field (``type``,
    ``cache_control``) via ``model_copy`` so the schema stays provider-valid.
    """
    update: dict[str, Any] = {}
    if tool.input_schema:
        update["input_schema"] = _strip_schema_descriptions(tool.input_schema)
    if shorten_desc and tool.description:
        update["description"] = _first_sentence(tool.description)
    if not update:
        return tool
    return tool.model_copy(update=update)


def compress_tools_to_budget(
    *,
    messages: Any,
    system: Any,
    tools: Sequence[Tool] | None,
    max_tokens: int,
    keep_names: frozenset[str],
    count_tokens: TokenCounter,
) -> tuple[list[Tool], bool]:
    """Shrink tool schemas (instead of dropping them) to fit ``max_tokens``.

    Returns ``(tools, changed)``. Only acts when the request is over budget:

    * **Level 1** strips ``input_schema`` prose from every tool while keeping each
      tool-level description. If that fits, we stop there.
    * **Level 2** additionally shortens the tool-level description to its first
      sentence for tools *not* in ``keep_names`` (core coding tools keep their full
      description). Returned best-effort even if still over budget.

    Every tool stays present — the caller may still drop tools afterwards if even
    full compression doesn't fit. A leaner tool always beats a missing one.
    """
    if not tools or max_tokens <= 0:
        return (list(tools) if tools else []), False
    if count_tokens(messages, system, tools) <= max_tokens:
        return list(tools), False

    level1 = [_compress_tool(tool, shorten_desc=False) for tool in tools]
    if count_tokens(messages, system, level1) <= max_tokens:
        return level1, True

    level2 = [
        _compress_tool(tool, shorten_desc=tool.name not in keep_names) for tool in tools
    ]
    return level2, True


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
