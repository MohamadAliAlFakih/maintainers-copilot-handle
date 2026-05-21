# Handle — Maintainer's Copilot

AIE Week 7 project. A fine-tuned classifier + advanced RAG + authenticated chatbot for triaging GitHub issues, embeddable as a React widget.

> **Status:** Plan 0a complete — infrastructure stack only. Backend code arrives in Plan 0b.

## Quick start

Prerequisites:

- Docker Engine 24+ with Compose v2
- Roughly 4 GB of RAM available to Docker
- `curl` (for the smoke test)

Steps:

```bash
git clone <repo>
cd handle
cp .env.example .env
# .env defaults are fine for local dev; review if you want
docker compose up -d --build
# wait ~90s for everything to settle, especially Langfuse
./scripts/check-stack.sh
```

The smoke test pings `/health` on every service. If everything passes, the stack is up cleanly.

## What's running

| Service | Port | Purpose |
|---|---|---|
| api | 8000 | FastAPI backend (currently a stub `/health` only) |
| modelserver | 8001 | FastAPI inference server (stub) |
| chatbot | 8501 | Streamlit UI (stub) |
| widget | 8080 | nginx serving the React widget bundle (stub) |
| host | 9000 | nginx serving the demo host page (stub) |
| db | 5432 | Postgres 16 + pgvector |
| redis | 6379 | Short-term memory + cache |
| minio | 9001 / 9002 | Blob storage (api + console) |
| vault | 8200 | Secrets (dev mode) |
| langfuse-web | 3001 | Tracing UI / API |
| langfuse-clickhouse | (internal) | Trace store |
| langfuse-db, langfuse-worker | (internal) | Langfuse internals |

Open `http://localhost:3001` for the Langfuse UI, `http://localhost:9002` for MinIO console, `http://localhost:8501` for the Streamlit stub.

## Layout

```
backend/        # FastAPI backend (real app arrives in Plan 0b)
modelserver/    # FastAPI inference server (real ML arrives in Plan 1)
chatbot/        # Streamlit UI (real pages arrive in Plan 4)
widget/         # React widget (real bundle arrives in Plan 5)
demo/host/      # Demo host page (real embed arrives in Plan 5)
infra/          # Postgres init, MinIO bucket setup, Vault secrets seed
scripts/        # Operational scripts (check-stack, etc.)
```

## Project standards

This project follows the AIE Bootcamp engineering standards: async everywhere, dependency injection via FastAPI `Depends()`, lifespan singletons for heavy resources, `pydantic-settings` for config, Pydantic at every boundary, structured logging with `structlog`, `uv` for Python env management, Alembic for migrations, redaction layer for sensitive values, `HTTPException` with correct status codes.

## Tear down

```bash
docker compose down -v
```

`-v` removes volumes (db data, MinIO blobs, Langfuse data). Drop it if you want to preserve state across boots.
