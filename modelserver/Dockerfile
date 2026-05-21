# Modelserver — classifier + NER + summarizer
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# download spaCy model into the venv
RUN uv run python -m spacy download en_core_web_sm

COPY app ./app
COPY prompts ./prompts

EXPOSE 8001

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
