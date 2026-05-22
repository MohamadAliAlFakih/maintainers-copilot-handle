"""HyDE query rewrite: turn the question into a hypothetical answer for embedding."""

from pathlib import Path

from openai import AsyncAzureOpenAI

from app.infra.logging_setup import get_logger

log = get_logger(__name__)


def _load_prompt(prompts_dir: Path) -> str:
    """Reads the HyDE prompt template from disk."""
    return (prompts_dir / "hyde_generate.md").read_text(encoding="utf-8")


async def generate_hypothetical_answer(
    client: AsyncAzureOpenAI,
    prompts_dir: Path,
    model: str,
    question: str,
    max_tokens: int = 300,
) -> str:
    """Calls the LLM to generate a 1-2 paragraph hypothetical answer for the question."""
    template = _load_prompt(prompts_dir)
    prompt = template.replace("{{ question }}", question)
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.2,
    )
    raw = (resp.choices[0].message.content or "").strip()
    log.info("hyde.generated", n_chars=len(raw), question=question[:80])
    return raw
