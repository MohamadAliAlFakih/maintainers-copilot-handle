"""LLM-based zero/few-shot classifier - produces bug/feature/docs/question or None."""

import re
from pathlib import Path
from typing import Literal

from openai import AsyncAzureOpenAI

from app.infra.llm import chat_complete
from app.infra.prompts import render_prompt

VALID_LABELS = {"bug", "feature", "docs", "question"}


def parse_llm_label(response: str) -> Literal["bug", "feature", "docs", "question"] | None:
    """Extracts one of the 4 classes from a free-form LLM response, or None if unmatched."""
    if not response:
        return None
    cleaned = response.strip().rstrip(".!?").lower()
    m = re.search(r"label\s*:\s*([a-z]+)", cleaned)
    if m:
        cleaned = m.group(1)
    else:
        words = re.findall(r"[a-z]+", cleaned)
        if not words:
            return None
        cleaned = words[-1]
    return cleaned if cleaned in VALID_LABELS else None  # type: ignore[return-value]


async def classify_with_llm(
    client: AsyncAzureOpenAI,
    prompts_dir: Path,
    model: str,
    issue_text: str,
) -> Literal["bug", "feature", "docs", "question"] | None:
    """Renders the classifier prompt, calls the LLM, parses the label. Returns None on failure."""
    rendered = render_prompt(prompts_dir, "classifier_llm", issue_text=issue_text)
    raw = await chat_complete(
        client,
        model=model,
        messages=[{"role": "user", "content": rendered}],
        max_tokens=16,
        temperature=0.0,
    )
    return parse_llm_label(raw)