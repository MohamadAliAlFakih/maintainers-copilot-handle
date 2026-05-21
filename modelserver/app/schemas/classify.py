"""Request/response shapes for /classify."""
from typing import Literal

from pydantic import BaseModel, Field


class ClassifyInput(BaseModel):
    """Issue text to classify."""

    text: str = Field(..., min_length=1, max_length=10_000)


class ClassifyResult(BaseModel):
    """Predicted class + confidence."""

    label: Literal["bug", "feature", "docs", "question"]
    confidence: float = Field(..., ge=0.0, le=1.0)
