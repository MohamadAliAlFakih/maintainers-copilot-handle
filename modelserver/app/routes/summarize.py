"""POST /summarize — LLM-driven issue-thread summary."""

from fastapi import APIRouter, Request

from app.config import get_settings
from app.infra.groq import chat_complete
from app.infra.prompts import render_prompt
from app.schemas.summarize import SummarizeInput, SummarizeResult

router = APIRouter()


def _bullets_from(summary: str) -> list[str]:
    """Splits the LLM output into individual bullet lines."""
    return [
        line.lstrip("- ").strip() for line in summary.splitlines() if line.strip().startswith("-")
    ]


@router.post("/summarize", response_model=SummarizeResult)
async def summarize(payload: SummarizeInput, request: Request) -> SummarizeResult:
    """Returns a 3-5 bullet summary of the thread."""
    settings = get_settings()
    client = request.app.state.groq

    rendered = render_prompt(settings.prompts_dir, "summarize_thread", thread_text=payload.thread)
    summary = await chat_complete(
        client,
        model=settings.groq_model_cheap,
        messages=[{"role": "user", "content": rendered}],
        max_tokens=300,
        temperature=0.1,
    )
    return SummarizeResult(summary=summary, bullets=_bullets_from(summary))
