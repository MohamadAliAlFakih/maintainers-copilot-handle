"""rag_search tool — runs RagOrchestrator, calls LLM for final answer, snapshots chunks."""
from pathlib import Path

from groq import AsyncGroq
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas.rag import RagQuery
from app.infra.logging_setup import get_logger
from app.services.rag.orchestrator import RagOrchestrator
from app.tools._base import ToolError, ToolResult

log = get_logger(__name__)

TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "rag_search",
        "description": (
            "Answer a maintainer's question using pandas docs and resolved-issue history. "
            "Returns a cited answer + the source paths used."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The maintainer's question"},
                "source_type": {
                    "type": "string",
                    "enum": ["doc", "resolved_issue", "any"],
                    "description": "Restrict retrieval to one source type, or 'any' for both.",
                    "default": "any",
                },
            },
            "required": ["question"],
        },
    },
}


class RagSearchArgs(BaseModel):
    """Typed args for rag_search."""

    question: str = Field(..., min_length=3, max_length=2000)
    source_type: str = Field("any")


def _build_context_text(hits: list) -> str:
    """Concatenates hits into a numbered context block for the answer prompt."""
    return "\n\n---\n\n".join(
        f"[{h.source_path}]\n{h.text}" for h in hits
    )


async def run_rag_search(
    args: RagSearchArgs,
    *,
    session: AsyncSession,
    orchestrator: RagOrchestrator,
    groq: AsyncGroq,
    prompts_dir: Path,
    answer_model: str = "llama-3.3-70b-versatile",
    conversation_id: str | None = None,
) -> ToolResult:
    """Retrieves chunks, generates an answer, returns answer + source paths."""
    try:
        ctx = await orchestrator.search(
            session,
            RagQuery(
                question=args.question,
                top_k=5,
                source_type=args.source_type,  # type: ignore[arg-type]
            ),
        )
    except Exception as e:  # noqa: BLE001
        log.exception("tool.rag_search.retrieve_failed")
        return ToolResult.failure(
            ToolError(error=f"retrieval failed: {e}", retryable=True)
        )

    if not ctx.hits:
        return ToolResult.ok(
            {
                "answer": "I couldn't find relevant context to answer that.",
                "sources": [],
            }
        )

    context_text = _build_context_text(ctx.hits)
    prompt = (prompts_dir / "rag_answer.md").read_text()
    rendered = prompt.replace("{{ question }}", args.question).replace(
        "{{ context }}", context_text
    )

    try:
        resp = await groq.chat.completions.create(
            model=answer_model,
            messages=[{"role": "user", "content": rendered}],
            max_tokens=600,
            temperature=0.1,
        )
        answer = (resp.choices[0].message.content or "").strip()
    except Exception as e:  # noqa: BLE001
        log.exception("tool.rag_search.generation_failed")
        return ToolResult.failure(ToolError(error=f"generation failed: {e}", retryable=True))

    sources = [h.source_path for h in ctx.hits]
    return ToolResult.ok({"answer": answer, "sources": sources, "_chunks_for_snapshot": [
        {
            "chunk_id": h.chunk_id,
            "source_path": h.source_path,
            "score": h.score,
            "text": h.text,
        }
        for h in ctx.hits
    ]})
