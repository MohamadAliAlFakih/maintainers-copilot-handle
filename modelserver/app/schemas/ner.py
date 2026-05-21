"""Schemas for /ner."""
from pydantic import BaseModel, Field


class NerInput(BaseModel):
    """Free-form text to extract entities from."""

    text: str = Field(..., min_length=1, max_length=10_000)


class Entity(BaseModel):
    """A single extracted entity with span info."""

    text: str
    type: str
    start: int
    end: int


class NerResult(BaseModel):
    """List of extracted entities."""

    entities: list[Entity]
