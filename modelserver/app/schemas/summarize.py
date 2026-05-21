"""Schemas for /summarize."""
from pydantic import BaseModel, Field


class SummarizeInput(BaseModel):
    """Full issue thread (title + body + comments) to summarize."""

    thread: str = Field(..., min_length=10, max_length=50_000)


class SummarizeResult(BaseModel):
    """A 3-5 bullet summary plus the raw text."""

    bullets: list[str]
    summary: str
