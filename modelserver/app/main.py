"""Modelserver FastAPI app - loads classifier + NER + LLM client at startup."""

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.infra.classifier_loader import (
    WeightsShaMismatch,
    load_classifier_from_minio,
)
from app.infra.embedder import load_embedders
from app.infra.llm import build_llm_client
from app.infra.logging_setup import configure_logging, get_logger
from app.infra.minio import build_minio_client
from app.infra.ner import build_ner_pipeline
from app.infra.reranker import load_reranker
from app.infra.vault import VaultClient
from app.routes import classify as classify_route
from app.routes import embed as embed_route
from app.routes import ner as ner_route
from app.routes import rerank as rerank_route
from app.routes import summarize as summarize_route

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Loads classifier + NER + LLM client at startup."""
    settings = get_settings()
    configure_logging(level=settings.log_level)
    log.info("modelserver.boot.begin")

    # ---- Vault first (for LLM credentials) ----
    vault = VaultClient(addr=settings.vault_addr, token=settings.vault_root_token)
    if not vault.is_authenticated():
        log.error("modelserver.boot.refused", reason="vault unreachable")
        print("[REFUSE TO BOOT] vault unreachable", file=sys.stderr)
        sys.exit(1)
    secrets = vault.load_secrets()
    if "placeholder" in secrets.llm_api_key:
        log.error("modelserver.boot.refused", reason="llm api key is placeholder")
        print(
            "[REFUSE TO BOOT] llm api key is still the placeholder; set it in Vault",
            file=sys.stderr,
        )
        sys.exit(1)

    # ---- Classifier ----
    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )
    try:
        loaded = load_classifier_from_minio(minio_client, settings.classifier_model_key)
    except WeightsShaMismatch as e:
        print(f"[REFUSE TO BOOT] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"[REFUSE TO BOOT] could not load classifier: {e}", file=sys.stderr)
        sys.exit(1)

    # ---- NER (spaCy) ----
    nlp = build_ner_pipeline()
    log.info("modelserver.ner_loaded")

    # ---- LLM client (Azure OpenAI) ----
    llm = build_llm_client(
        api_key=secrets.llm_api_key,
        endpoint=secrets.llm_endpoint,
        api_version=secrets.llm_api_version,
        timeout=settings.llm_request_timeout,
    )

    # ---- Embedders (BGE + MiniLM) ----
    embedders = load_embedders(settings.embedder_primary, settings.embedder_challenger)

    # ---- Reranker (cross-encoder) ----
    reranker = load_reranker(settings.reranker_model)

    # ---- Attach to app.state ----
    app.state.classifier = loaded
    app.state.ner_pipeline = nlp
    app.state.llm = llm
    app.state.llm_deployment = secrets.llm_deployment
    app.state.embedders = embedders
    app.state.reranker = reranker

    log.info("modelserver.boot.done", weights_sha=loaded.weights_sha[:12])
    yield

    log.info("modelserver.shutdown.begin")
    await llm.close()
    log.info("modelserver.shutdown.done")


app = FastAPI(title="Handle Modelserver", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok", "service": "modelserver"}


app.include_router(classify_route.router)
app.include_router(ner_route.router)
app.include_router(summarize_route.router)
app.include_router(embed_route.router)
app.include_router(rerank_route.router)