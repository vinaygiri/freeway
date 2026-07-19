"""Anthropic SSE serialization helpers."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

ANTHROPIC_SSE_RESPONSE_HEADERS: dict[str, str] = {
    "X-Accel-Buffering": "no",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}

STOP_REASON_MAP = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "content_filter": "end_turn",
}

# Free-tier providers are inconsistent with finish_reason. These non-standard
# values all mean "output was truncated" — map them to max_tokens so the
# truncation is NEVER masked as a clean stop (which would make a client stop
# mid-task). Matched case-insensitively.
_TRUNCATION_ALIASES = frozenset(
    {
        "max_tokens",
        "max_output_tokens",
        "maxtokens",
        "model_length",
        "token_limit",
        "output_limit",
        "length_limit",
        "max_completion_tokens",
    }
)
# Non-standard "the model wants to call a tool" values.
_TOOL_ALIASES = frozenset({"function_call", "tool_call", "tool_use"})


def map_stop_reason(openai_reason: str | None) -> str:
    """Map OpenAI ``finish_reason`` to Anthropic ``stop_reason``, robustly.

    Normalizes case and recognizes common non-standard provider values so a
    truncation is never silently reported as a clean ``end_turn`` (which would
    make a coding agent stop mid-task). Genuinely unknown values default to
    ``end_turn`` (the safe assumption for a provider that finished normally with
    a quirky value)."""
    if not openai_reason:
        return "end_turn"
    key = openai_reason.strip().lower()
    if key in STOP_REASON_MAP:
        return STOP_REASON_MAP[key]
    if key in _TRUNCATION_ALIASES:
        return "max_tokens"
    if key in _TOOL_ALIASES:
        return "tool_use"
    return "end_turn"


def format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format one Anthropic-style SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


class AnthropicSseEmitter:
    """Serialize Anthropic SSE events and optionally log raw event bodies."""

    def __init__(self, *, log_raw_events: bool = False) -> None:
        self._log_raw_events = log_raw_events

    def event(self, event_type: str, data: dict[str, Any]) -> str:
        event = format_sse_event(event_type, data)
        if self._log_raw_events:
            logger.debug("SSE_EVENT: {} - {}", event_type, event.strip())
        return event
