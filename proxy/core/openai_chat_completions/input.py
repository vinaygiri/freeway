"""Convert OpenAI Chat Completions requests into Anthropic Messages payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import ChatCompletionsConversionError
from .ids import new_tool_call_id
from .tools import convert_tool_choice, convert_tools, parse_arguments


def convert_request_to_anthropic_payload(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert an OpenAI Chat Completions request into an Anthropic Messages payload."""

    raw_messages = request.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ChatCompletionsConversionError(
            "Chat Completions request must include a non-empty messages list"
        )

    system_parts: list[str] = []
    messages: list[dict[str, Any]] = []
    pending_tool_results: list[dict[str, Any]] = []

    def flush_tool_results() -> None:
        if pending_tool_results:
            messages.append({"role": "user", "content": list(pending_tool_results)})
            pending_tool_results.clear()

    for item in raw_messages:
        if not isinstance(item, dict):
            raise ChatCompletionsConversionError(
                f"Unsupported Chat Completions message: {type(item).__name__}"
            )
        role = item.get("role")
        if role in ("system", "developer"):
            flush_tool_results()
            if text := _content_as_text(item.get("content")):
                system_parts.append(text)
            continue
        if role == "tool":
            call_id = item.get("tool_call_id")
            if not isinstance(call_id, str) or not call_id:
                raise ChatCompletionsConversionError(
                    "Chat Completions tool message must include tool_call_id"
                )
            pending_tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call_id,
                    "content": _content_as_text(item.get("content")),
                }
            )
            continue
        flush_tool_results()
        if role == "user":
            messages.append(
                {"role": "user", "content": _convert_content(item.get("content"))}
            )
            continue
        if role == "assistant":
            messages.append(_convert_assistant_message(item))
            continue
        raise ChatCompletionsConversionError(
            f"Unsupported Chat Completions message role: {role!r}"
        )

    flush_tool_results()

    if not messages:
        raise ChatCompletionsConversionError(
            "Chat Completions request must contain a user or assistant message"
        )

    payload: dict[str, Any] = {
        "model": _required_model(request.get("model")),
        "messages": messages,
        "stream": True,
    }
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)
    if request.get("temperature") is not None:
        payload["temperature"] = request["temperature"]
    if request.get("top_p") is not None:
        payload["top_p"] = request["top_p"]

    max_tokens = request.get("max_completion_tokens")
    if max_tokens is None:
        max_tokens = request.get("max_tokens")
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    stop = request.get("stop")
    if isinstance(stop, str):
        payload["stop_sequences"] = [stop]
    elif isinstance(stop, list):
        sequences = [value for value in stop if isinstance(value, str)]
        if sequences:
            payload["stop_sequences"] = sequences

    if isinstance(request.get("metadata"), dict):
        payload["metadata"] = request["metadata"]

    raw_tool_choice = request.get("tool_choice")
    tools = convert_tools(request.get("tools"))
    if tools and raw_tool_choice != "none":
        payload["tools"] = tools
    tool_choice = convert_tool_choice(raw_tool_choice)
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice

    return payload


def _convert_assistant_message(item: Mapping[str, Any]) -> dict[str, Any]:
    tool_calls = item.get("tool_calls")
    content = item.get("content")
    if not tool_calls:
        return {"role": "assistant", "content": _convert_content(content)}

    if not isinstance(tool_calls, list):
        raise ChatCompletionsConversionError(
            "Chat Completions assistant tool_calls must be a list"
        )

    blocks: list[dict[str, Any]] = []
    if text := _content_as_text(content):
        blocks.append({"type": "text", "text": text})
    for call in tool_calls:
        if not isinstance(call, dict):
            raise ChatCompletionsConversionError(
                "Chat Completions tool_call must be an object"
            )
        function = call.get("function")
        source = function if isinstance(function, dict) else {}
        name = source.get("name")
        if not isinstance(name, str) or not name:
            raise ChatCompletionsConversionError(
                "Chat Completions tool_call.function.name must be a non-empty string"
            )
        call_id = call.get("id")
        blocks.append(
            {
                "type": "tool_use",
                "id": call_id
                if isinstance(call_id, str) and call_id
                else new_tool_call_id(),
                "name": name,
                "input": parse_arguments(source.get("arguments")),
            }
        )
    return {"role": "assistant", "content": blocks}


def _convert_content(content: Any) -> str | list[dict[str, Any]]:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        blocks: list[dict[str, Any]] = []
        for part in content:
            if isinstance(part, str):
                blocks.append({"type": "text", "text": part})
                continue
            if not isinstance(part, dict):
                raise ChatCompletionsConversionError(
                    f"Unsupported Chat Completions content part: {type(part).__name__}"
                )
            part_type = part.get("type")
            if part_type in {"text", "input_text", "output_text"} or "text" in part:
                blocks.append({"type": "text", "text": _text_of(part)})
                continue
            if part_type == "image_url":
                blocks.append(_image_block(part.get("image_url")))
                continue
            raise ChatCompletionsConversionError(
                f"Unsupported Chat Completions content part type: {part_type!r}"
            )
        return blocks
    raise ChatCompletionsConversionError(
        f"Unsupported Chat Completions message content: {type(content).__name__}"
    )


def _image_block(image_url: Any) -> dict[str, Any]:
    url = image_url.get("url") if isinstance(image_url, dict) else image_url
    if not isinstance(url, str) or not url:
        raise ChatCompletionsConversionError(
            "Chat Completions image_url must include a url"
        )
    if url.startswith("data:"):
        try:
            header, data = url.split(",", 1)
            media_type = header[len("data:") : header.index(";")]
        except (ValueError, IndexError) as exc:
            raise ChatCompletionsConversionError(
                "Chat Completions image data URL is malformed"
            ) from exc
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        }
    return {"type": "image", "source": {"type": "url", "url": url}}


def _content_as_text(content: Any) -> str:
    converted = _convert_content(content)
    if isinstance(converted, str):
        return converted
    return "\n".join(
        str(block.get("text", "")) for block in converted if block.get("type") == "text"
    )


def _text_of(part: Mapping[str, Any]) -> str:
    text = part.get("text")
    return text if isinstance(text, str) else ""


def _required_model(value: Any) -> str:
    if isinstance(value, str) and value:
        return value
    raise ChatCompletionsConversionError("Chat Completions request must include model")
