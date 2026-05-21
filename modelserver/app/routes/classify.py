"""POST /classify — runs the loaded RoBERTa model on the input text."""

import torch
from fastapi import APIRouter, Request

from app.infra.classifier_loader import ID_TO_LABEL
from app.schemas.classify import ClassifyInput, ClassifyResult

router = APIRouter()


@router.post("/classify", response_model=ClassifyResult)
async def classify(payload: ClassifyInput, request: Request) -> ClassifyResult:
    """Returns the predicted class and softmax confidence for the issue text."""
    loaded = request.app.state.classifier
    tok = loaded.tokenizer
    model = loaded.model

    enc = tok(
        payload.text,
        truncation=True,
        max_length=256,
        padding="max_length",
        return_tensors="pt",
    )

    with torch.no_grad():
        logits = model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"]).logits
        probs = torch.softmax(logits, dim=-1).squeeze(0)
        pred = int(torch.argmax(probs).item())
        confidence = float(probs[pred].item())

    return ClassifyResult(label=ID_TO_LABEL[pred], confidence=confidence)  # type: ignore[arg-type]
