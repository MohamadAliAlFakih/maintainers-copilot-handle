"""POST /embed — batch embed with BGE and/or MiniLM."""

from fastapi import APIRouter, Request

from app.infra.embedder import embed_batch
from app.schemas.embed import EmbedInput, EmbedResult

router = APIRouter()


@router.post("/embed", response_model=EmbedResult)
async def embed(payload: EmbedInput, request: Request) -> EmbedResult:
    """Runs each requested embedder over the input texts."""
    loaded = request.app.state.embedders
    result = EmbedResult()
    if payload.which in {"bge", "both"}:
        result.bge = embed_batch(loaded.bge, payload.texts)
    if payload.which in {"minilm", "both"}:
        result.minilm = embed_batch(loaded.minilm, payload.texts)
    return result
