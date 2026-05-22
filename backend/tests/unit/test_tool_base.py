"""Tests for tool base helpers."""

from app.tools._base import ToolError, ToolResult


def test_tool_error_is_serializable():
    """ToolError converts to a dict the LLM can read."""
    err = ToolError(error="upstream unreachable", retryable=True)
    d = err.to_dict()
    assert d["error"] == "upstream unreachable"
    assert d["retryable"] is True


def test_tool_result_wraps_success_payload():
    """ToolResult.ok(payload) sets ok=True and value=payload."""
    r = ToolResult.ok({"label": "bug"})
    assert r.ok is True
    assert r.value == {"label": "bug"}
    assert r.error is None


def test_tool_result_wraps_failure():
    """ToolResult.failure(err) sets ok=False, value=None, error=err."""
    r = ToolResult.failure(ToolError(error="x", retryable=False))
    assert r.ok is False
    assert r.error.error == "x"
