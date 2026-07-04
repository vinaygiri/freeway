"""Identifier helpers for Chat Completions output."""

from __future__ import annotations

import uuid


def new_completion_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:24]}"


def new_tool_call_id() -> str:
    return f"call_{uuid.uuid4().hex[:24]}"
