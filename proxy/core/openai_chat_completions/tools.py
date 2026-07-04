"""Tool conversion helpers for the OpenAI Chat Completions adapter.

Chat Completions tools use a flat ``function`` shape and 1:1 tool names, so the
conversion is simpler than the Responses adapter (no namespaces / custom tools).
"""

from __future__ import annotations

import json
from typing import Any

from .errors import ChatCompletionsConversionError


def convert_tools(value: Any) -> list[dict[str, Any]] | None:
    """Convert OpenAI Chat Completions tools into Anthropic tools."""

    if value is None:
        return None
    if not isinstance(value, list):
        raise ChatCompletionsConversionError("Chat Completions tools must be a list")

    tools: list[dict[str, Any]] = []
    for tool in value:
        if not isinstance(tool, dict):
            raise ChatCompletionsConversionError(
                f"Unsupported Chat Completions tool: {type(tool).__name__}"
            )
        if tool.get("type") not in (None, "function"):
            # Skip provider-specific non-function tool types rather than failing.
            continue
        function = tool.get("function")
        source = function if isinstance(function, dict) else tool
        name = source.get("name")
        if not isinstance(name, str) or not name:
            raise ChatCompletionsConversionError(
                "Chat Completions tool.function.name must be a non-empty string"
            )
        schema = source.get("parameters")
        if schema is None:
            schema = {"type": "object", "properties": {}}
        if not isinstance(schema, dict):
            raise ChatCompletionsConversionError(
                f"Chat Completions tool {name!r} parameters must be an object"
            )
        converted: dict[str, Any] = {"name": name, "input_schema": schema}
        description = source.get("description")
        if isinstance(description, str) and description:
            converted["description"] = description
        tools.append(converted)
    return tools


def convert_tool_choice(value: Any) -> dict[str, Any] | None:
    """Convert an OpenAI Chat Completions tool_choice into an Anthropic tool_choice."""

    if value is None or value in ("auto", "none"):
        return None
    if value == "required":
        return {"type": "any"}
    if isinstance(value, dict) and value.get("type") == "function":
        function = value.get("function")
        source = function if isinstance(function, dict) else value
        name = source.get("name")
        if isinstance(name, str) and name:
            return {"type": "tool", "name": name}
    raise ChatCompletionsConversionError(
        f"Unsupported Chat Completions tool_choice: {value!r}"
    )


def parse_arguments(value: Any) -> dict[str, Any]:
    """Parse OpenAI function-call arguments (a JSON string) into a dict."""

    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        raise ChatCompletionsConversionError(
            "Chat Completions tool call arguments must be a JSON string"
        )
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ChatCompletionsConversionError(
            f"Chat Completions tool call arguments are invalid JSON: {exc.msg}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ChatCompletionsConversionError(
            "Chat Completions tool call arguments must decode to an object"
        )
    return parsed
