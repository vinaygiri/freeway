"""Assemble OpenAI Chat Completions output from an Anthropic SSE event stream.

Supports both streaming (per-event ``chat.completion.chunk`` emission) and
non-streaming aggregation into a single ``chat.completion`` object.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import Any

from .anthropic_sse import AnthropicSseEvent
from .errors import openai_error_payload
from .ids import new_completion_id, new_tool_call_id

_FINISH_REASONS = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "tool_use": "tool_calls",
    "max_tokens": "length",
}


class _ToolCall:
    __slots__ = ("argument_parts", "call_id", "index", "name")

    def __init__(self, index: int, call_id: str, name: str) -> None:
        self.index = index
        self.call_id = call_id
        self.name = name
        self.argument_parts: list[str] = []

    @property
    def arguments(self) -> str:
        return "".join(self.argument_parts)


class ChatCompletionAssembler:
    """Translate Anthropic SSE events into Chat Completions output."""

    def __init__(self, request: Mapping[str, Any]) -> None:
        self._request = request
        self._id = new_completion_id()
        self._created = int(time.time())
        self._model = str(request.get("model", ""))
        self._started = False
        self.terminal = False
        self._content_parts: list[str] = []
        self._reasoning_parts: list[str] = []
        self._tool_calls: dict[int, _ToolCall] = {}
        self._tool_order: list[int] = []
        self._next_tool_index = 0
        self._finish_reason: str | None = None
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._error: dict[str, Any] | None = None

    # -- streaming --------------------------------------------------------
    def process_anthropic_event(self, event: AnthropicSseEvent) -> list[str]:
        if self.terminal:
            return []
        chunks = self._ensure_started()
        name = event.event
        if name == "message_start":
            self._record_usage(_message_usage(event.data))
        elif name == "content_block_start":
            chunks.extend(self._handle_block_start(event.data))
        elif name == "content_block_delta":
            chunks.extend(self._handle_block_delta(event.data))
        elif name == "message_delta":
            self._record_message_delta(event.data)
        elif name == "message_stop":
            chunks.extend(self._finish())
        elif name == "error":
            chunks.extend(self._fail(event.data))
        return chunks

    def finish_if_needed(self) -> list[str]:
        if self.terminal:
            return []
        chunks = self._ensure_started()
        chunks.extend(self._finish())
        return chunks

    def _ensure_started(self) -> list[str]:
        if self._started:
            return []
        self._started = True
        return [self._chunk({"role": "assistant"})]

    def _handle_block_start(self, data: Mapping[str, Any]) -> list[str]:
        block = data.get("content_block")
        if not isinstance(block, dict):
            return []
        block_type = block.get("type")
        if block_type == "text":
            return self._text_delta(_str(block.get("text")))
        if block_type == "thinking":
            return self._reasoning_delta(_str(block.get("thinking")))
        if block_type == "tool_use":
            index = _event_index(data)
            if index is None:
                return []
            call = _ToolCall(
                index=self._next_tool_index,
                call_id=_str(block.get("id")) or new_tool_call_id(),
                name=_str(block.get("name")),
            )
            self._next_tool_index += 1
            self._tool_calls[index] = call
            self._tool_order.append(index)
            function: dict[str, Any] = {"name": call.name, "arguments": ""}
            initial = block.get("input")
            if isinstance(initial, dict) and initial:
                arguments = json.dumps(initial, separators=(",", ":"))
                call.argument_parts.append(arguments)
                function["arguments"] = arguments
            return [
                self._chunk(
                    {
                        "tool_calls": [
                            {
                                "index": call.index,
                                "id": call.call_id,
                                "type": "function",
                                "function": function,
                            }
                        ]
                    }
                )
            ]
        return []

    def _handle_block_delta(self, data: Mapping[str, Any]) -> list[str]:
        delta = data.get("delta")
        if not isinstance(delta, dict):
            return []
        delta_type = delta.get("type")
        if delta_type == "text_delta":
            return self._text_delta(_str(delta.get("text")))
        if delta_type == "thinking_delta":
            return self._reasoning_delta(_str(delta.get("thinking")))
        if delta_type == "input_json_delta":
            index = _event_index(data)
            call = self._tool_calls.get(index) if index is not None else None
            if call is None:
                return []
            partial = _str(delta.get("partial_json"))
            if not partial:
                return []
            call.argument_parts.append(partial)
            return [
                self._chunk(
                    {
                        "tool_calls": [
                            {"index": call.index, "function": {"arguments": partial}}
                        ]
                    }
                )
            ]
        return []

    def _text_delta(self, text: str) -> list[str]:
        if not text:
            return []
        self._content_parts.append(text)
        return [self._chunk({"content": text})]

    def _reasoning_delta(self, text: str) -> list[str]:
        if not text:
            return []
        self._reasoning_parts.append(text)
        return [self._chunk({"reasoning_content": text})]

    def _record_message_delta(self, data: Mapping[str, Any]) -> None:
        delta = data.get("delta")
        if isinstance(delta, dict):
            stop_reason = delta.get("stop_reason")
            if isinstance(stop_reason, str):
                self._finish_reason = _FINISH_REASONS.get(stop_reason, "stop")
        self._record_usage(data.get("usage"))

    def _record_usage(self, usage: Any) -> None:
        if not isinstance(usage, dict):
            return
        if isinstance(usage.get("input_tokens"), int):
            self._prompt_tokens = usage["input_tokens"]
        if isinstance(usage.get("output_tokens"), int):
            self._completion_tokens = usage["output_tokens"]

    def _finish(self) -> list[str]:
        if self.terminal:
            return []
        self.terminal = True
        chunks = [self._chunk({}, finish_reason=self._resolved_finish_reason())]
        if self._include_usage():
            chunks.append(self._usage_chunk())
        return chunks

    def _fail(self, data: Mapping[str, Any]) -> list[str]:
        if self.terminal:
            return []
        self.terminal = True
        self._error = _error_from_anthropic(data)
        return [_sse(self._error)]

    def _resolved_finish_reason(self) -> str:
        if self._finish_reason:
            return self._finish_reason
        return "tool_calls" if self._tool_calls else "stop"

    def _include_usage(self) -> bool:
        options = self._request.get("stream_options")
        return isinstance(options, dict) and bool(options.get("include_usage"))

    def _chunk(
        self, delta: Mapping[str, Any], *, finish_reason: str | None = None
    ) -> str:
        return _sse(
            {
                "id": self._id,
                "object": "chat.completion.chunk",
                "created": self._created,
                "model": self._model,
                "choices": [
                    {"index": 0, "delta": delta, "finish_reason": finish_reason}
                ],
            }
        )

    def _usage_chunk(self) -> str:
        return _sse(
            {
                "id": self._id,
                "object": "chat.completion.chunk",
                "created": self._created,
                "model": self._model,
                "choices": [],
                "usage": self._usage(),
            }
        )

    def _usage(self) -> dict[str, int]:
        return {
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens,
            "total_tokens": self._prompt_tokens + self._completion_tokens,
        }

    # -- non-streaming aggregation ---------------------------------------
    def completion(self) -> dict[str, Any]:
        content = "".join(self._content_parts)
        tool_calls = [
            {
                "id": self._tool_calls[index].call_id,
                "type": "function",
                "function": {
                    "name": self._tool_calls[index].name,
                    "arguments": self._tool_calls[index].arguments or "{}",
                },
            }
            for index in self._tool_order
        ]
        message: dict[str, Any] = {"role": "assistant"}
        message["content"] = content if (content or not tool_calls) else None
        if self._reasoning_parts:
            message["reasoning_content"] = "".join(self._reasoning_parts)
        if tool_calls:
            message["tool_calls"] = tool_calls
        return {
            "id": self._id,
            "object": "chat.completion",
            "created": self._created,
            "model": self._model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": self._resolved_finish_reason(),
                }
            ],
            "usage": self._usage(),
        }

    @property
    def error(self) -> dict[str, Any] | None:
        return self._error


def _error_from_anthropic(data: Mapping[str, Any]) -> dict[str, Any]:
    error = data.get("error")
    if isinstance(error, Mapping):
        message = error.get("message")
        error_type = error.get("type")
        return openai_error_payload(
            message=message if isinstance(message, str) else "provider error",
            error_type=error_type if isinstance(error_type, str) else "api_error",
        )
    return openai_error_payload(message="provider error", error_type="api_error")


def _message_usage(data: Mapping[str, Any]) -> Any:
    message = data.get("message")
    return message.get("usage") if isinstance(message, dict) else None


def _sse(payload: Mapping[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _event_index(data: Mapping[str, Any]) -> int | None:
    value = data.get("index")
    return value if isinstance(value, int) else None


def _str(value: Any) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)
