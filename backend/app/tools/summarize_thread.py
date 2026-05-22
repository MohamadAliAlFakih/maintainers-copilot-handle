"""summarize_thread tool â€” wraps modelserver /summarize."""

import httpx
from pydantic import BaseModel, Field

from app.infra.tracing import observe
from app.tools._base import ToolError, ToolResult

MODELSERVER_URL = "http://modelserver:8001"

TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "summarize_thread",
        "description": "Summarize a GitHub issue thread (title + body + comments) into 3-5 bullets.",
        "parameters": {
            "type": "object",
            "properties": {
                "thread": {
                    "type": "string",
                    "description": "Full thread text",
                }
            },
            "required": ["thread"],
        },
    },
}


class SummarizeThreadArgs(BaseModel):
    """Typed args for summarize_thread."""

    thread: str = Field(..., min_length=10, max_length=50_000)


@observe(name="tool.summarize_thread")
async def run_summarize_thread(args: SummarizeThreadArgs, http: httpx.AsyncClient) -> ToolResult:
    """Calls modelserver /summarize."""
    try:
        r = await http.post(
            f"{MODELSERVER_URL}/summarize",
            json={"thread": args.thread},
            timeout=60.0,
        )
        if r.status_code >= 400:
            retryable = r.status_code >= 500
            return ToolResult.failure(
                ToolError(error=f"modelserver returned {r.status_code}", retryable=retryable)
            )
        body = r.json()
        return ToolResult.ok({"summary": body["summary"], "bullets": body["bullets"]})
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        return ToolResult.failure(ToolError(error=f"modelserver unreachable: {e}", retryable=True))
