"""POST /rerank — cross-encoder reranks the candidate passages."""

from fastapi import APIRouter, Request

from app.infra.reranker import rerank
from app.schemas.rerank import RerankHit, RerankInput, RerankResult

router = APIRouter()


@router.post("/rerank", response_model=RerankResult)
async def rerank_endpoint(payload: RerankInput, request: Request) -> RerankResult:
    """Runs the cross-encoder over query x passages, returns top_k by score."""
    enc = request.app.state.reranker
    hits = rerank(enc, payload.query, payload.passages, payload.top_k)
    return RerankResult(hits=[RerankHit(index=i, score=s) for i, s in hits])
