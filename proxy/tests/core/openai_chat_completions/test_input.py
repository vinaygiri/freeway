from __future__ import annotations

import pytest

from core.openai_chat_completions.errors import ChatCompletionsConversionError
from core.openai_chat_completions.input import convert_request_to_anthropic_payload


def _convert(**request):
    return convert_request_to_anthropic_payload(request)


def test_system_message_hoisted_to_system_field():
    payload = _convert(
        model="m",
        messages=[
            {"role": "system", "content": "Be terse."},
            {"role": "developer", "content": "Prefer Python."},
            {"role": "user", "content": "hi"},
        ],
    )
    assert payload["system"] == "Be terse.\n\nPrefer Python."
    assert payload["messages"] == [{"role": "user", "content": "hi"}]
    assert payload["stream"] is True


def test_assistant_tool_calls_become_tool_use_blocks():
    payload = _convert(
        model="m",
        messages=[
            {"role": "user", "content": "go"},
            {
                "role": "assistant",
                "content": "sure",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "echo", "arguments": '{"v":1}'},
                    }
                ],
            },
        ],
    )
    assistant = payload["messages"][1]
    assert assistant["role"] == "assistant"
    assert assistant["content"][0] == {"type": "text", "text": "sure"}
    assert assistant["content"][1] == {
        "type": "tool_use",
        "id": "call_1",
        "name": "echo",
        "input": {"v": 1},
    }


def test_consecutive_tool_messages_merge_into_one_user_message():
    payload = _convert(
        model="m",
        messages=[
            {"role": "user", "content": "go"},
            {"role": "tool", "tool_call_id": "a", "content": "ra"},
            {"role": "tool", "tool_call_id": "b", "content": "rb"},
            {"role": "user", "content": "next"},
        ],
    )
    tool_message = payload["messages"][1]
    assert tool_message["role"] == "user"
    assert [block["tool_use_id"] for block in tool_message["content"]] == ["a", "b"]
    assert payload["messages"][2] == {"role": "user", "content": "next"}


def test_max_completion_tokens_preferred_and_stop_normalized():
    payload = _convert(
        model="m",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=100,
        max_completion_tokens=50,
        stop="STOP",
    )
    assert payload["max_tokens"] == 50
    assert payload["stop_sequences"] == ["STOP"]

    payload_list = _convert(
        model="m",
        messages=[{"role": "user", "content": "hi"}],
        stop=["a", "b"],
    )
    assert payload_list["stop_sequences"] == ["a", "b"]


def test_tool_choice_variants():
    base = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
    tools = [{"type": "function", "function": {"name": "echo", "parameters": {}}}]

    required = _convert(**base, tools=tools, tool_choice="required")
    assert required["tool_choice"] == {"type": "any"}

    forced = _convert(
        **base,
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "echo"}},
    )
    assert forced["tool_choice"] == {"type": "tool", "name": "echo"}

    none = _convert(**base, tools=tools, tool_choice="none")
    assert "tools" not in none
    assert "tool_choice" not in none


def test_image_url_parts_convert_to_anthropic_image_blocks():
    payload = _convert(
        model="m",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "what is this"},
                    {"type": "image_url", "image_url": {"url": "https://x/y.png"}},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,QUJD"},
                    },
                ],
            }
        ],
    )
    blocks = payload["messages"][0]["content"]
    assert blocks[0] == {"type": "text", "text": "what is this"}
    assert blocks[1] == {
        "type": "image",
        "source": {"type": "url", "url": "https://x/y.png"},
    }
    assert blocks[2] == {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": "QUJD"},
    }


@pytest.mark.parametrize(
    "request_kwargs",
    [
        {"model": "m", "messages": []},
        {"model": "m", "messages": [{"role": "banana", "content": "x"}]},
        {"model": "", "messages": [{"role": "user", "content": "x"}]},
    ],
)
def test_invalid_requests_raise_conversion_error(request_kwargs):
    with pytest.raises(ChatCompletionsConversionError):
        convert_request_to_anthropic_payload(request_kwargs)


def test_bad_tool_call_arguments_raise():
    with pytest.raises(ChatCompletionsConversionError):
        _convert(
            model="m",
            messages=[
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "echo", "arguments": "{bad json"},
                        }
                    ],
                }
            ],
        )
