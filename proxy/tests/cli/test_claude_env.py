"""Tests for Claude Code launcher env sizing (auto-compact window)."""

from __future__ import annotations

from cli.claude_env import resolve_auto_compact_window
from cli.launchers.claude import build_claude_launcher_env


def test_compact_window_uses_budget_when_set() -> None:
    # Explicit AUTO_FIT_MAX_TOKENS wins.
    assert resolve_auto_compact_window(8000, 128000, 190000) == 8000


def test_compact_window_derives_from_model_context() -> None:
    # No explicit budget -> 90% of the model's advertised context.
    assert resolve_auto_compact_window(0, 128000, 190000) == 115200


def test_compact_window_falls_back_to_default_when_unknown() -> None:
    # No budget and unknown context -> unchanged 200k default (behavior preserved).
    assert resolve_auto_compact_window(0, None, 190000) == 190000
    assert resolve_auto_compact_window(-1, None, 190000) == 190000


def test_launcher_env_injects_sized_window() -> None:
    env = build_claude_launcher_env(
        proxy_root_url="http://127.0.0.1:8082",
        auth_token="tok",
        base_env={},
        auto_compact_window=8000,
    )
    assert env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == "8000"
    assert env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:8082"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "tok"
