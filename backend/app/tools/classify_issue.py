"""classify_issue tool â€” wraps modelserver /classify behind a typed Pydantic input."""

import httpx
from pydantic import BaseModel, Field

from app.infra.tracing import observe
from app.tools._base import ToolError, ToolResult

log = get_logger(__name__)

MODELSERVER_URL = "http://modelserver:8001"

# Groq tool spec for this tool (matches OpenAI function-calling schema)
TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "classify_issue",
        "description": "Classify a GitHub issue text into bug/feature/docs/question with a confidence score.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The issue title + body to classify",
                }
            },
            "required": ["text"],
        },
    },
}


class ClassifyIssueArgs(BaseModel):
    """Typed args used to validate the LLM's tool-call arguments."""

    text: str = Field(..., min_length=10, max_length=10_000)


@observe(name="tool.classify_issue")
async def run_classify_issue(args: ClassifyIssueArgs, http: httpx.AsyncClient) -> ToolResult:
    """Calls modelserver /classify; returns ToolResult.ok or ToolResult.failure."""
    try:
        r = await http.post(f"{MODELSERVER_URL}/classify", json={"text": args.text}, timeout=30.0)
        if r.status_code >= 500:
            return ToolResult.failure(
                ToolError(error=f"modelserver returned {r.status_code}", retryable=True)
            )
        if r.status_code >= 400:
            return ToolResult.failure(
                ToolError(error=f"modelserver returned {r.status_code}", retryable=False)
            )
        body = r.json()
        return ToolResult.ok({"label": body["label"], "confidence": body["confidence"]})
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        log.warning("tool.classify_issue.network", error=str(e))
        return ToolResult.failure(ToolError(error=f"modelserver unreachable: {e}", retryable=True))
