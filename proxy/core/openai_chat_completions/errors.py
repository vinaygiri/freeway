"""Errors and error envelopes for OpenAI Chat Completions compatibility."""

from __future__ import annotations

from typing import Any


class ChatCompletionsConversionError(ValueError):
    """Raised when a Chat Completions request cannot be converted deterministically."""


class ChatCompletionsStreamError(Exception):
    """Raised when the upstream stream fails during non-streaming aggregation.

    Carries an OpenAI-compatible error envelope so the handler can return it.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__("chat completions stream error")
        self.payload = payload


def openai_error_payload(*, message: str, error_type: str) -> dict[str, Any]:
    """Return an OpenAI-compatible error envelope."""

    return {
        "error": {
            "message": message,
            "type": error_type,
            "param": None,
            "code": None,
        }
    }
