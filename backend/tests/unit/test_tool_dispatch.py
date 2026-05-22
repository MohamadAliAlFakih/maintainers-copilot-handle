"""Tests for the tool-dispatch layer of the chat loop."""
from unittest.mock import AsyncMock

import pytest

from app.services.chat.loop import dispatch_tool


@pytest.mark.asyncio
async def test_dispatch_classify_calls_classify_tool(monkeypatch):
    """A tool_call for classify_issue dispatches to run_classify_issue with parsed args."""
    fake = AsyncMock(return_value=type("R", (), {"ok": True, "value": {"label": "bug"}, "error": None, "to_llm_payload": lambda self=None: {"ok": True, "value": {"label": "bug"}}})())
    monkeypatch.setattr("app.services.chat.loop.run_classify_issue", fake)

    result = await dispatch_tool(
        name="classify_issue",
        arguments_json='{"text":"My pandas app crashes with TypeError on read_csv"}',
        deps={"http": object()},
    )
    assert result["ok"] is True
    fake.assert_awaited()


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_error_payload():
    """An unknown tool name yields a structured error payload."""
    result = await dispatch_tool(
        name="not_a_real_tool",
        arguments_json="{}",
        deps={},
    )
    assert result["ok"] is False
    assert "unknown tool" in result["error"]["error"].lower()


@pytest.mark.asyncio
async def test_dispatch_malformed_args_returns_error():
    """Args that don't parse to the tool's Pydantic shape produce a structured error."""
    result = await dispatch_tool(
        name="classify_issue",
        arguments_json='{"WRONG_FIELD":"x"}',
        deps={"http": object()},
    )
    assert result["ok"] is False
