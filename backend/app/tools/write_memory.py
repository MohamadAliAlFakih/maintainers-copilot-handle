"""write_memory tool Ã¢â‚¬â€ persists a fact to long-term memory with redaction + audit log."""

import uuid

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.logging_setup import get_logger
from app.infra.tracing import observe
from app.services.memory.long_term import remember_fact
from app.tools._base import ToolError, ToolResult

log = get_logger(__name__)

TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "write_memory",
        "description": (
            "Persist a single concise fact the user explicitly told you about themselves "
            "or their preferences. NEVER call on chitchat or hypotheticals."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "A single concise fact, <= 200 chars",
                }
            },
            "required": ["fact"],
        },
    },
}


class WriteMemoryArgs(BaseModel):
    """Typed args for write_memory."""

    fact: str = Field(..., min_length=3, max_length=500)


@observe(name="tool.write_memory")
async def run_write_memory(
    args: WriteMemoryArgs,
    *,
    session: AsyncSession,
    http: httpx.AsyncClient,
    user_id: uuid.UUID,
) -> ToolResult:
    """Persists the fact via the long-term memory service."""
    try:
        result = await remember_fact(
            session=session,
            http=http,
            user_id=user_id,
            fact_text=args.fact,
        )
        return ToolResult.ok({"saved": True, "fact": result["fact"]})
    except Exception as e:  # noqa: BLE001
        log.exception("tool.write_memory.failed")
        return ToolResult.failure(ToolError(error=f"could not save memory: {e}", retryable=False))
