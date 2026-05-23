"""Frozen-judge wrapper: builds the prompt, calls the LLM, parses the score."""

import re
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncAzureOpenAI


@dataclass(frozen=True)
class JudgeScore:
    """Two-dimensional judge output. Both fields are 1..5 integers."""

    faithfulness: int
    answer_relevancy: int


def parse_judge_response(raw: str) -> JudgeScore | None:
    """Extracts faithfulness + answer_relevancy from the LLM's response. None on malformed."""
    if not raw:
        return None
    f_match = re.search(r"faithfulness\s*:\s*([1-5])", raw, re.IGNORECASE)
    r_match = re.search(r"answer_relevancy\s*:\s*([1-5])", raw, re.IGNORECASE)
    if not f_match or not r_match:
        return None
    return JudgeScore(
        faithfulness=int(f_match.group(1)),
        answer_relevancy=int(r_match.group(1)),
    )


async def judge_answer(
    client: AsyncAzureOpenAI,
    prompt_template: str,
    model: str,
    question: str,
    ideal_answer: str,
    context: str,
    candidate_answer: str,
) -> JudgeScore | None:
    """Calls the frozen judge model. Returns None if the response is unparseable."""
    rendered = (
        prompt_template.replace("{{ question }}", question)
        .replace("{{ ideal_answer }}", ideal_answer)
        .replace("{{ context }}", context)
        .replace("{{ candidate_answer }}", candidate_answer)
    )
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": rendered}],
        max_tokens=64,
        temperature=0.0,
    )
    raw = (resp.choices[0].message.content or "").strip()
    return parse_judge_response(raw)


def load_judge_prompt(path: Path) -> str:
    """Reads the judge prompt template."""
    return path.read_text(encoding="utf-8")
