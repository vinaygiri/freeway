"""Strip unwanted tool definitions from inbound requests.

Editor clients (Claude Code, etc.) attach every registered tool's full JSON
schema to *every* request. On small free-tier token budgets those schemas alone
can blow past the provider's per-minute limit before any real content is sent.
``DROP_TOOLS`` lets an operator drop tools they don't need (fnmatch globs) so the
forwarded request is smaller — without touching the client's config.
"""

from __future__ import annotations

from collections.abc import Sequence
from fnmatch import fnmatch
from typing import Protocol


class _NamedTool(Protocol):
    name: str


def parse_drop_tools(spec: str) -> tuple[str, ...]:
    """Parse a comma-separated ``DROP_TOOLS`` spec into fnmatch patterns."""
    return tuple(pattern.strip() for pattern in spec.split(",") if pattern.strip())


def should_drop_tool(name: str, patterns: Sequence[str]) -> bool:
    """Return whether a tool name matches any drop pattern (case-insensitive)."""
    lowered = name.lower()
    return any(fnmatch(lowered, pattern.lower()) for pattern in patterns)


def filter_tools[T: _NamedTool](
    tools: Sequence[T] | None, patterns: Sequence[str]
) -> list[T] | None:
    """Return ``tools`` without entries matching ``patterns``.

    Returns the input unchanged (as a list) when nothing is dropped, and ``None``
    when every tool is dropped or the input was falsy — mirroring the "no tools"
    shape expected by the request models.
    """
    if not tools or not patterns:
        return list(tools) if tools else None
    kept = [tool for tool in tools if not should_drop_tool(tool.name, patterns)]
    return kept or None
