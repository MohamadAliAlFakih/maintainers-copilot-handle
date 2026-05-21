# Backend image with alembic + app code
FROM python:3.12-slim AS base

# install git (used by fetch_docs.py sparse-checkout)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /usr/local/bin/uv

WORKDIR /app

# install deps first for cache
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# copy alembic, app source, admin scripts, and prompts
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY prompts ./prompts

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
