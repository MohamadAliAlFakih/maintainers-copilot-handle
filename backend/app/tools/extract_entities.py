"""extract_entities tool â€” wraps modelserver /ner."""

import httpx
from pydantic import BaseModel, Field

from app.infra.tracing import observe
from app.tools._base import ToolError, ToolResult

MODELSERVER_URL = "http://modelserver:8001"

TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "extract_entities",
        "description": "Extract code-shaped entities (versions, decorators, modules, exceptions, issue refs) from text.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Issue text to extract entities from"}
            },
            "required": ["text"],
        },
    },
}


class ExtractEntitiesArgs(BaseModel):
    """Typed args for extract_entities."""

    text: str = Field(..., min_length=1, max_length=10_000)


@observe(name="tool.extract_entities")
async def run_extract_entities(args: ExtractEntitiesArgs, http: httpx.AsyncClient) -> ToolResult:
    """Calls modelserver /ner; returns ToolResult."""
    try:
        r = await http.post(f"{MODELSERVER_URL}/ner", json={"text": args.text}, timeout=30.0)
        if r.status_code >= 400:
            retryable = r.status_code >= 500
            return ToolResult.failure(
                ToolError(error=f"modelserver returned {r.status_code}", retryable=retryable)
            )
        return ToolResult.ok({"entities": r.json()["entities"]})
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        return ToolResult.failure(ToolError(error=f"modelserver unreachable: {e}", retryable=True))
