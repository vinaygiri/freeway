"""Translate Anthropic SSE streams into OpenAI Chat Completions output."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Mapping
from typing import Any

from .anthropic_sse import iter_sse_events
from .assembler import ChatCompletionAssembler
from .errors import ChatCompletionsStreamError

_DONE = "data: [DONE]\n\n"


async def iter_chat_sse_from_anthropic(
    chunks: AsyncIterable[Any],
    request: Mapping[str, Any],
) -> AsyncIterator[str]:
    """Yield Chat Completions SSE events translated from an Anthropic SSE stream."""

    assembler = ChatCompletionAssembler(request)
    async for event in iter_sse_events(chunks):
        for chunk in assembler.process_anthropic_event(event):
            yield chunk
        if assembler.terminal:
            break
    else:
        for chunk in assembler.finish_if_needed():
            yield chunk
    # OpenAI streams terminate with a sentinel on success; a mid-stream error
    # is delivered as an error chunk instead.
    if assembler.error is None:
        yield _DONE


async def aggregate_chat_completion_from_anthropic(
    chunks: AsyncIterable[Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a single non-streaming ``chat.completion`` object."""

    assembler = ChatCompletionAssembler(request)
    async for event in iter_sse_events(chunks):
        assembler.process_anthropic_event(event)
        if assembler.terminal:
            break
    else:
        assembler.finish_if_needed()
    if assembler.error is not None:
        raise ChatCompletionsStreamError(assembler.error)
    return assembler.completion()
