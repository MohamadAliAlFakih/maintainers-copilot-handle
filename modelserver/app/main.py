"""Stub modelserver — classifier, NER, summarizer arrive in Plan 1."""
from fastapi import FastAPI

app = FastAPI(title="Handle Modelserver (stub)")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check for docker healthcheck."""
    return {"status": "ok", "service": "modelserver"}
