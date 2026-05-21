"""DTOs for RAG queries and results."""

from typing import Literal

from pydantic import BaseModel, Field


class RagQuery(BaseModel):
    """Inbound RAG query — used by the chatbot's rag_search tool."""

    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=20)
    source_type: Literal["doc", "resolved_issue", "any"] = "any"


class RagHit(BaseModel):
    """One retrieved-and-reranked chunk to feed back to the LLM."""

    chunk_id: str
    text: str
    source_type: str
    source_path: str
    section_headers: list[str]
    score: float


class RagAnswerContext(BaseModel):
    """Bundle of retrieved hits + the hypothetical answer used to retrieve them."""

    hits: list[RagHit]
    hypothetical_answer: str
