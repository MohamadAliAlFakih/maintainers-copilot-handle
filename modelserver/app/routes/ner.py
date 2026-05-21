"""POST /ner — extracts code-shaped entities."""

from fastapi import APIRouter, Request

from app.infra.ner import extract_entities
from app.schemas.ner import Entity, NerInput, NerResult

router = APIRouter()


@router.post("/ner", response_model=NerResult)
async def ner(payload: NerInput, request: Request) -> NerResult:
    """Returns entities found in the input text."""
    nlp = request.app.state.ner_pipeline
    ents = extract_entities(nlp, payload.text)
    return NerResult(entities=[Entity(**e) for e in ents])
