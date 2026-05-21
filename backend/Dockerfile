# Backend image with alembic + app code
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /usr/local/bin/uv

WORKDIR /app

# install deps first for cache
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# copy alembic, app source, and admin scripts
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
