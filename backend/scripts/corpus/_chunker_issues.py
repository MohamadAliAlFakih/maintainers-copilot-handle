"""Resolved-issue chunker: 1 chunk if short, else split into (title+body) and (answer)."""

import hashlib
from typing import Any

import tiktoken

from app.services.rag.chunker import Chunk

_ENC = tiktoken.get_encoding("cl100k_base")
_MAX_TOKENS = 1000


def _make_id(issue_number: int, part: str) -> str:
    """Deterministic chunk_id for an issue chunk."""
    return hashlib.sha256(f"issues/{issue_number}|{part}".encode()).hexdigest()[:32]


def chunk_issue(issue: dict[str, Any]) -> list[Chunk]:
    """Turns a resolved-issue dict into one or two chunks."""
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    answer = issue.get("best_answer") or ""
    n_issue = issue["issue_number"]
    src = f"issues/{n_issue}"

    full_text = f"# Issue #{n_issue}: {title}\n\n{body}"
    if answer:
        full_text_with_answer = full_text + f"\n\n## Maintainer answer\n\n{answer}"
    else:
        full_text_with_answer = full_text

    total_tokens = len(_ENC.encode(full_text_with_answer))

    if total_tokens <= _MAX_TOKENS or not answer:
        return [
            Chunk(
                text=full_text_with_answer,
                source_type="resolved_issue",
                source_path=src,
                section_headers=[f"#{n_issue} {title}"],
                chunk_id=_make_id(n_issue, "all"),
            )
        ]

    return [
        Chunk(
            text=full_text,
            source_type="resolved_issue",
            source_path=src,
            section_headers=[f"#{n_issue} {title}"],
            chunk_id=_make_id(n_issue, "body"),
        ),
        Chunk(
            text=f"# Maintainer answer for #{n_issue}\n\n{answer}",
            source_type="resolved_issue",
            source_path=src,
            section_headers=[f"#{n_issue} answer"],
            chunk_id=_make_id(n_issue, "answer"),
        ),
    ]
