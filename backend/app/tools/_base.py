"""Shared tool building blocks: typed result wrapper, ToolError, registry helpers."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolError:
    """Failure return shape from a tool. LLM sees this and decides what to do next."""

    error: str
    retryable: bool

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict form for serializing back into the tool-result message to the LLM."""
        return {"error": self.error, "retryable": self.retryable}


@dataclass
class ToolResult:
    """Either a successful value or a ToolError. Never raises."""

    ok: bool
    value: Any = None
    error: ToolError | None = None

    @classmethod
    def ok(cls, value: Any) -> "ToolResult":
        """Construct a successful result."""
        return cls(ok=True, value=value)

    @classmethod
    def failure(cls, error: ToolError) -> "ToolResult":
        """Construct a failure result."""
        return cls(ok=False, error=error)

    def to_llm_payload(self) -> dict[str, Any]:
        """Serializes the result for the tool-message back to the LLM."""
        if self.ok:
            return {"ok": True, "value": self.value}
        return {"ok": False, "error": self.error.to_dict() if self.error else {"error": "unknown"}}
