"""Pydantic models for OpenAI Chat Completions-compatible ingress."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ChatCompletionsRequest(BaseModel):
    """Permissive subset of the OpenAI Chat Completions API request shape."""

    model_config = ConfigDict(extra="allow")

    model: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any = None
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    # Chat Completions defaults to non-streaming when ``stream`` is omitted.
    stream: bool | None = None
    stream_options: dict[str, Any] | None = None
    stop: str | list[str] | None = None
    n: int | None = None
    metadata: dict[str, Any] | None = None
