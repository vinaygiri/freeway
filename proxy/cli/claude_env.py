"""Shared Claude Code environment policy for FCC client surfaces."""

from __future__ import annotations

CLAUDE_CODE_AUTO_COMPACT_WINDOW = "190000"
CLAUDE_BINARY_NAME = "claude"
CLAUDE_NO_AUTH_SENTINEL = "freeway-no-auth"


def resolve_auto_compact_window(
    auto_fit_max_tokens: int, model_context: int | None, default_window: int
) -> int:
    """Size Claude Code's compaction window to the routed model's real budget.

    Priority: an explicit ``AUTO_FIT_MAX_TOKENS`` (the operator's real per-request
    budget) → 90% of the primary model's advertised context → the 200k default.
    So Claude Code compacts *before* the conversation outgrows the free model,
    instead of growing toward the Anthropic-sized default and getting rejected.
    """
    if auto_fit_max_tokens and auto_fit_max_tokens > 0:
        return auto_fit_max_tokens
    if model_context and model_context > 0:
        return int(model_context * 0.9)
    return default_window


def claude_auth_token(auth_token: str) -> str:
    """Return the Claude Code auth marker for proxy-auth or no-auth sessions."""

    return auth_token.strip() or CLAUDE_NO_AUTH_SENTINEL
