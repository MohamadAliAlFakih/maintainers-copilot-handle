"""write_memory tool — STUB in Plan 4a. Full impl with pgvector in Plan 4b."""
from pydantic import BaseModel, Field

from app.infra.logging_setup import get_logger
from app.tools._base import ToolResult

log = get_logger(__name__)

TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "write_memory",
        "description": (
            "Persist a single concise fact the user explicitly told you about themselves "
            "or their preferences. Never call this on chitchat — only on direct statements."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "A single concise fact (e.g., 'user prefers terse summaries')",
                }
            },
            "required": ["fact"],
        },
    },
}


class WriteMemoryArgs(BaseModel):
    """Typed args for write_memory."""

    fact: str = Field(..., min_length=3, max_length=500)


async def run_write_memory(args: WriteMemoryArgs) -> ToolResult:
    """Stub: just logs. Plan 4b replaces this with pgvector persistence + audit log."""
    log.info("tool.write_memory.stub", fact=args.fact)
    return ToolResult.ok({"saved": True, "fact": args.fact})
