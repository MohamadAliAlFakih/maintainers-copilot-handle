"""Schemas for /embed."""

from typing import Literal

from pydantic import BaseModel, Field


class EmbedInput(BaseModel):
    """Batch of texts to embed with both models."""

    texts: list[str] = Field(..., min_length=1, max_length=64)
    which: Literal["bge", "minilm", "both"] = "both"


class EmbedResult(BaseModel):
    """Embeddings keyed by model name; missing if 'which' excluded it."""

    bge: list[list[float]] | None = None
    minilm: list[list[float]] | None = None
