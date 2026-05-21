"""Modelserver FastAPI app — loads classifier + NER + Groq at startup."""
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.infra.classifier_loader import (
    WeightsShaMismatch,
    load_classifier_from_minio,
)
from app.infra.groq import build_groq_client
from app.infra.logging_setup import configure_logging, get_logger
from app.infra.minio import build_minio_client
from app.infra.ner import build_ner_pipeline
from app.infra.vault import VaultClient
from app.routes import classify as classify_route
from app.routes import ner as ner_route
from app.routes import summarize as summarize_route

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Loads classifier + NER + Groq client at startup."""
    settings = get_settings()
    configure_logging(level=settings.log_level)
    log.info("modelserver.boot.begin")

    # ---- Vault first (for Groq key) ----
    vault = VaultClient(addr=settings.vault_addr, token=settings.vault_root_token)
    if not vault.is_authenticated():
        log.error("modelserver.boot.refused", reason="vault unreachable")
        print("[REFUSE TO BOOT] vault unreachable", file=sys.stderr)
        sys.exit(1)
    secrets = vault.load_secrets()
    if "placeholder" in secrets.groq_api_key:
        log.error("modelserver.boot.refused", reason="groq api key is placeholder")
        print(
            "[REFUSE TO BOOT] groq api key is still the placeholder; set it in Vault",
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

    # ---- Groq ----
    groq = build_groq_client(
        api_key=secrets.groq_api_key, timeout=settings.groq_request_timeout
    )

    # ---- Attach to app.state ----
    app.state.classifier = loaded
    app.state.ner_pipeline = nlp
    app.state.groq = groq

    log.info("modelserver.boot.done", weights_sha=loaded.weights_sha[:12])
    yield

    log.info("modelserver.shutdown.begin")
    await groq.close()
    log.info("modelserver.shutdown.done")


app = FastAPI(title="Handle Modelserver", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok", "service": "modelserver"}


app.include_router(classify_route.router)
app.include_router(ner_route.router)
app.include_router(summarize_route.router)
