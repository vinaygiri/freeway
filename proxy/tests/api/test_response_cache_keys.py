"""Tests for exact-match cache key + cacheability policy."""

from __future__ import annotations

from typing import Any

from api.models.anthropic import Message, MessagesRequest, Tool
from api.response_cache_keys import cache_key, is_cacheable


def _request(**overrides: Any) -> MessagesRequest:
    base: dict[str, Any] = {
        "model": "nvidia_nim/test-model",
        "max_tokens": 100,
        "messages": [Message(role="user", content="hi")],
        "temperature": 0,
    }
    base.update(overrides)
    return MessagesRequest(**base)


def test_cacheable_when_no_tools_and_zero_temperature() -> None:
    assert is_cacheable(_request()) is True


def test_not_cacheable_without_explicit_zero_temperature() -> None:
    # Default temperature is None; only an explicit 0 is deterministic-ish.
    assert is_cacheable(_request(temperature=None)) is False


def test_not_cacheable_with_nonzero_temperature() -> None:
    assert is_cacheable(_request(temperature=0.7)) is False


def test_not_cacheable_with_tools() -> None:
    tool = Tool(name="get_weather", input_schema={"type": "object"})
    assert is_cacheable(_request(tools=[tool])) is False


def test_identical_requests_share_key() -> None:
    assert cache_key(_request()) == cache_key(_request())


def test_different_content_changes_key() -> None:
    a = _request(messages=[Message(role="user", content="one")])
    b = _request(messages=[Message(role="user", content="two")])
    assert cache_key(a) != cache_key(b)


def test_volatile_fields_excluded_from_key() -> None:
    # stream + metadata are volatile transport/per-call fields.
    a = _request(stream=True, metadata={"user_id": "alice"})
    b = _request(stream=False, metadata={"user_id": "bob"})
    assert cache_key(a) == cache_key(b)


def test_model_changes_key() -> None:
    a = _request(model="nvidia_nim/model-a")
    b = _request(model="nvidia_nim/model-b")
    assert cache_key(a) != cache_key(b)
