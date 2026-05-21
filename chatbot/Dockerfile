# Streamlit stub container
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app.py ./

EXPOSE 8501

# streamlit needs --server.address=0.0.0.0 to be reachable from outside the container
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
