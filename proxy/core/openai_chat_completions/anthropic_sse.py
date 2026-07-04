"""Anthropic SSE parsing used by the Chat Completions stream adapter.

Self-contained (mirrors the parser in ``core/openai_responses``) so the Chat
Completions adapter does not import another adapter's internals. Both could be
consolidated into ``core/anthropic`` in a later refactor.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AnthropicSseEvent:
    event: str
    data: dict[str, Any]


async def iter_sse_events(
    chunks: AsyncIterable[Any],
) -> AsyncIterator[AnthropicSseEvent]:
    buffer = ""
    async for chunk in chunks:
        if isinstance(chunk, bytes):
            buffer += chunk.decode("utf-8", errors="replace")
        else:
            buffer += str(chunk)

        while "\n\n" in buffer:
            raw, buffer = buffer.split("\n\n", 1)
            event = parse_sse_event(raw)
            if event is not None:
                yield event

    if buffer.strip():
        event = parse_sse_event(buffer)
        if event is not None:
            yield event


def parse_sse_event(raw: str) -> AnthropicSseEvent | None:
    event_type = ""
    data_parts: list[str] = []
    for line in raw.splitlines():
        stripped = line.rstrip("\r")
        if stripped.startswith("event:"):
            event_type = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("data:"):
            data_parts.append(stripped.split(":", 1)[1].strip())
    if not event_type and not data_parts:
        return None
    data_text = "\n".join(data_parts)
    if data_text == "[DONE]":
        return None
    try:
        parsed = json.loads(data_text) if data_text else {}
    except json.JSONDecodeError:
        parsed = {"raw": data_text}
    if not isinstance(parsed, dict):
        parsed = {"value": parsed}
    return AnthropicSseEvent(event=event_type, data=parsed)
