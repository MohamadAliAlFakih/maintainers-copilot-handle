"""Schemas for /rerank."""

from pydantic import BaseModel, Field


class RerankInput(BaseModel):
    """Query + candidate passages; reranker returns top_k by relevance."""

    query: str = Field(..., min_length=1, max_length=2000)
    passages: list[str] = Field(..., min_length=1, max_length=100)
    top_k: int = Field(5, ge=1, le=50)


class RerankHit(BaseModel):
    """One reranked passage (by index into input.passages) with its score."""

    index: int
    score: float


class RerankResult(BaseModel):
    """Top-k reranker output."""

    hits: list[RerankHit]
