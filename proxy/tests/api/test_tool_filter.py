"""Tests for DROP_TOOLS request tool-stripping."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.responses import StreamingResponse

from api.handlers import MessagesHandler
from api.models.anthropic import Message, MessagesRequest, Tool
from api.tool_filter import filter_tools, parse_drop_tools, should_drop_tool
from config.settings import Settings
from providers.base import BaseProvider, ProviderConfig


def _tool(name: str, filler: str = "") -> Tool:
    return Tool(name=name, description=filler, input_schema={"type": "object"})


# ----------------------- pure helpers -----------------------


def test_parse_drop_tools_splits_and_trims() -> None:
    assert parse_drop_tools(" Workflow , Task* ,,") == ("Workflow", "Task*")
    assert parse_drop_tools("") == ()


def test_should_drop_tool_glob_and_case_insensitive() -> None:
    pats = parse_drop_tools("Workflow,Task*,Cron*")
    assert should_drop_tool("Workflow", pats)
    assert should_drop_tool("workflow", pats)  # case-insensitive
    assert should_drop_tool("TaskCreate", pats)
    assert should_drop_tool("CronДelete".replace("Д", "D"), pats)
    assert not should_drop_tool("Bash", pats)
    assert not should_drop_tool("Read", pats)


def test_filter_tools_drops_matching() -> None:
    tools = [_tool("Workflow"), _tool("Bash"), _tool("TaskCreate"), _tool("Read")]
    kept = filter_tools(tools, parse_drop_tools("Workflow,Task*"))
    assert kept is not None
    assert [t.name for t in kept] == ["Bash", "Read"]


def test_filter_tools_none_when_all_dropped() -> None:
    tools = [_tool("Workflow"), _tool("TaskCreate")]
    assert filter_tools(tools, parse_drop_tools("Workflow,Task*")) is None


def test_filter_tools_noop_without_patterns() -> None:
    tools = [_tool("Bash")]
    kept = filter_tools(tools, ())
    assert kept is not None and [t.name for t in kept] == ["Bash"]
    assert filter_tools(None, parse_drop_tools("Workflow")) is None


# ----------------------- handler integration -----------------------


class _RecordingProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(ProviderConfig(api_key="test"))
        self.received: list[Any] = []

    def preflight_stream(
        self, request: Any, *, thinking_enabled: bool | None = None
    ) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    async def list_model_ids(self) -> frozenset[str]:
        return frozenset({"test-model"})

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        self.received.append(request)
        yield 'event: message_start\ndata: {"type":"message_start"}\n\n'
        yield 'event: message_stop\ndata: {"type":"message_stop"}\n\n'


def _settings_with_drop(spec: str) -> Settings:
    settings = Settings()
    settings.drop_tools = spec
    return settings


async def _drain(response: object) -> None:
    assert isinstance(response, StreamingResponse)
    async for _ in response.body_iterator:
        pass


@pytest.mark.asyncio
async def test_handler_strips_dropped_tools_before_provider() -> None:
    provider = _RecordingProvider()
    handler = MessagesHandler(
        _settings_with_drop("Workflow,Task*,Cron*"),
        provider_getter=lambda _: provider,
    )
    request = MessagesRequest(
        model="nvidia_nim/test-model",
        max_tokens=100,
        messages=[Message(role="user", content="hi")],
        tools=[
            _tool("Workflow"),
            _tool("TaskCreate"),
            _tool("CronList"),
            _tool("Bash"),
            _tool("Read"),
        ],
    )

    await _drain(handler.create(request))

    forwarded = provider.received[0].tools
    assert [t.name for t in forwarded] == ["Bash", "Read"]


@pytest.mark.asyncio
async def test_handler_keeps_all_tools_when_drop_unset() -> None:
    provider = _RecordingProvider()
    handler = MessagesHandler(Settings(), provider_getter=lambda _: provider)
    request = MessagesRequest(
        model="nvidia_nim/test-model",
        max_tokens=100,
        messages=[Message(role="user", content="hi")],
        tools=[_tool("Workflow"), _tool("Bash")],
    )

    await _drain(handler.create(request))

    assert [t.name for t in provider.received[0].tools] == ["Workflow", "Bash"]


# --------- proof against the user's real captured tool sizes ---------


def test_reduction_matches_real_capture() -> None:
    """Using the user's real tool sizes: 91.5k chars -> ~16k after DROP_TOOLS."""
    # (name, approx char size) from the captured breakdown.
    captured = {
        "Workflow": 21577,
        "DesignSync": 9338,
        "AskUserQuestion": 5052,
        "EnterPlanMode": 4324,
        "CronCreate": 4137,
        "EnterWorktree": 3811,
        "ScheduleWakeup": 3811,
        "TaskUpdate": 3612,
        "Grep": 3345,
        "Bash": 2928,
        "Agent": 2887,
        "TaskCreate": 2869,
        "ExitPlanMode": 2589,
        "ExitWorktree": 2560,
        "Skill": 2149,
        "ReportFindings": 2123,
        "Read": 1701,
        "NotebookEdit": 1693,
        "TaskOutput": 1613,
        "SendMessage": 1303,
        "TaskList": 1215,
        "TaskGet": 1050,
        "Edit": 1020,
        "WebSearch": 889,
        "TaskStop": 840,
        "WebFetch": 790,
        "Glob": 768,
        "Write": 677,
        "CronDelete": 459,
        "CronList": 303,
    }
    tools = [_tool(name, "x" * size) for name, size in captured.items()]

    def total_chars(ts: list[Tool] | None) -> int:
        return sum(len(json.dumps(t.model_dump(), default=str)) for t in (ts or []))

    before = total_chars(tools)
    assert before > 90_000  # matches the ~91k capture

    drop = "Workflow,DesignSync,EnterPlanMode,ExitPlanMode,Cron*,EnterWorktree,ExitWorktree,ScheduleWakeup,Task*,Agent,SendMessage,Skill,ReportFindings"
    kept = filter_tools(tools, parse_drop_tools(drop))

    kept_names = {t.name for t in (kept or [])}
    assert kept_names == {
        "AskUserQuestion",
        "Grep",
        "Bash",
        "Read",
        "NotebookEdit",
        "Edit",
        "WebSearch",
        "WebFetch",
        "Glob",
        "Write",
    }
    after = total_chars(kept)
    # ~91k -> ~22k chars of tool schemas: the orchestration bulk is gone.
    assert after < 25_000
