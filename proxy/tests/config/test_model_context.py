"""Tests for parsing model context windows (used to auto-size auto-fit)."""

from __future__ import annotations

from config.model_quality import context_tokens_for, parse_context_tokens


def test_parse_context_tokens_variants() -> None:
    assert parse_context_tokens("128k") == 128_000
    assert parse_context_tokens("1M") == 1_000_000
    assert parse_context_tokens("8192") == 8192
    assert parse_context_tokens("200K") == 200_000


def test_parse_context_tokens_unknown() -> None:
    assert parse_context_tokens("-") is None
    assert parse_context_tokens("") is None
    assert parse_context_tokens("lots") is None


def test_context_tokens_for_known_and_unknown() -> None:
    # A catalogued model resolves to a positive token count; unknown -> None.
    assert context_tokens_for("does-not-exist-xyz") is None
    ctx = context_tokens_for("meta/llama-4-maverick-17b-128e-instruct")
    assert ctx == 1_000_000
