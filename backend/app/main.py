"""FastAPI app entrypoint — lifespan singletons, exception handler, refuse-to-boot."""

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from groq import AsyncGroq

from app.api.routes import health
from app.api.routes import users as users_routes
from app.config import get_settings
from app.domain.exceptions import DomainError
from app.domain.schemas.user import UserCreate, UserRead
from app.infra.db import build_engine, build_session_factory
from app.infra.logging_setup import configure_logging, get_logger
from app.infra.minio import build_minio_client
from app.infra.redis_client import build_redis_client
from app.infra.startup_checks import StartupFailure, check_chunks_not_empty, run_all_checks
from app.infra.tracing import build_langfuse_client
from app.infra.vault import VaultClient
from app.services.auth.strategy import build_jwt_strategy

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Boots singletons in order; aborts on any startup-check failure."""
    settings = get_settings()
    configure_logging(level=settings.log_level)

    log.info("app.boot.begin", environment=settings.environment)

    # --- Vault first (we need secrets to build the other clients) ---
    vault = VaultClient(addr=settings.vault_addr, token=settings.vault_root_token)

    # --- MinIO (built with env creds first so the bucket check can run) ---
    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )

    # --- Fetch secrets early so we can validate the JWT key in the check ---
    try:
        if not vault.is_authenticated():
            raise StartupFailure("Vault unreachable; cannot fetch secrets")
        secrets = vault.load_all_secrets()
    except StartupFailure as e:
        log.error("app.boot.refused", reason=str(e))
        print(f"[REFUSE TO BOOT] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        log.error("app.boot.refused", reason=f"unable to read secrets from Vault: {e}")
        print(f"[REFUSE TO BOOT] unable to read secrets from Vault: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Refuse-to-boot checks (now including JWT placeholder check) ---
    from pathlib import Path

    try:
        run_all_checks(
            settings,
            vault,
            minio_client,
            secrets.jwt_signing_key,
            prompts_dir=Path("/app/prompts"),
            thresholds_path=Path("/app/evals/eval_thresholds.yaml"),
        )
    except StartupFailure as e:
        log.error("app.boot.refused", reason=str(e))
        print(f"[REFUSE TO BOOT] {e}", file=sys.stderr)
        sys.exit(1)

    # --- Build JWT strategy with Vault-loaded signing key ---
    jwt_strategy = build_jwt_strategy(
        signing_key=secrets.jwt_signing_key,
        lifetime_seconds=settings.jwt_lifetime_seconds,
    )

    # --- Build remaining singletons ---
    redis_client = build_redis_client(host=settings.redis_host, port=settings.redis_port)
    engine = build_engine(dsn=settings.db_dsn)
    session_factory = build_session_factory(engine)

    # --- Async refuse-to-boot: corpus must be ingested before serving RAG ---
    try:
        await check_chunks_not_empty(session_factory)
    except StartupFailure as e:
        log.error("app.boot.refused", reason=str(e))
        print(f"[REFUSE TO BOOT] {e}", file=sys.stderr)
        sys.exit(1)

    langfuse = build_langfuse_client(
        host=settings.langfuse_host,
        public_key=secrets.langfuse_public_key,
        secret_key=secrets.langfuse_secret_key,
    )

    # --- Groq client (api-side, used by HyDE and the chatbot) ---
    groq_client = AsyncGroq(api_key=secrets.groq_api_key, timeout=60.0)

    # --- httpx client for modelserver calls (kept open for the process lifetime) ---
    modelserver_http = httpx.AsyncClient(timeout=60.0)

    # --- Attach to app.state ---
    app.state.settings = settings
    app.state.vault_secrets = secrets
    app.state.minio = minio_client
    app.state.redis = redis_client
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.langfuse = langfuse
    app.state.jwt_strategy = jwt_strategy
    app.state.groq = groq_client
    app.state.modelserver_http = modelserver_http

    log.info("app.boot.done")

    try:
        yield
    finally:
        log.info("app.shutdown.begin")
        await modelserver_http.aclose()
        await groq_client.close()
        await redis_client.aclose()
        await engine.dispose()
        log.info("app.shutdown.done")


app = FastAPI(title="Handle API", lifespan=lifespan)

# Dynamic CORS — origin allowlist comes from each widget's allowed_origins (DB)
from app.api.middleware.cors import DynamicCorsMiddleware  # noqa: E402

app.add_middleware(DynamicCorsMiddleware)


@app.exception_handler(DomainError)
async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
    """Maps domain exceptions to structured HTTP responses."""
    log.warning("domain_error", code=exc.code, message=exc.message)
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(Exception)
async def handle_uncaught(_request: Request, exc: Exception) -> JSONResponse:
    """Catches anything not otherwise handled — never leaks stack traces to the client."""
    log.exception("uncaught_exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal", "message": "An internal error occurred"}},
    )


# --- Routers ---
# Local imports to avoid forcing fastapi-users module import before tests can monkeypatch.
from app.api.dependencies import auth_backend, fastapi_users  # noqa: E402

app.include_router(health.router)

# /auth/jwt/login + /auth/jwt/logout
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
# /auth/register
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
# our own /users/me
app.include_router(users_routes.router, prefix="/users", tags=["users"])

# /chat/stream — tool-calling chatbot
from app.api.routes import chat as chat_routes  # noqa: E402

app.include_router(chat_routes.router, tags=["chat"])

# /memory/* — long-term memory inspector (user own + admin view)
from app.api.routes import memory as memory_routes  # noqa: E402

app.include_router(memory_routes.router, prefix="/memory", tags=["memory"])

# /admin/widgets/* — widget CRUD (admin only)
from app.api.routes import widget_admin as widget_admin_routes  # noqa: E402

app.include_router(widget_admin_routes.router, prefix="/admin/widgets", tags=["widget-admin"])

# /widgets/{id}/config — public widget config endpoint
from app.api.routes import widget as widget_routes  # noqa: E402

app.include_router(widget_routes.router, tags=["widget"])

# /widget.js loader + /widget/{id}/embed HTML wrapper (CSP frame-ancestors)
from app.api.routes import widget_loader as widget_loader_routes  # noqa: E402

app.include_router(widget_loader_routes.router, tags=["widget"])
