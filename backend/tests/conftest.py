"""Shared pytest fixtures and env scaffolding."""

import socket

import pytest


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sets the minimum env vars Settings needs so tests don't hit the real .env."""
    monkeypatch.setenv("VAULT_ADDR", "http://vault.test:8200")
    monkeypatch.setenv("VAULT_ROOT_TOKEN", "test-root-token")
    monkeypatch.setenv("DB_USER", "test-user")
    monkeypatch.setenv("DB_PASSWORD", "test-password")
    monkeypatch.setenv("DB_NAME", "test-db")
    monkeypatch.setenv("DB_HOST", "db.test")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("REDIS_HOST", "redis.test")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("MINIO_ENDPOINT", "minio.test:9000")
    monkeypatch.setenv("MINIO_ROOT_USER", "test-minio-user")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "test-minio-password")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse.test:3000")


@pytest.fixture
def real_db_dsn(monkeypatch: pytest.MonkeyPatch) -> str:
    """Provides the dsn for the dockerized DB; tests skip if it's not running."""
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    dsn = "postgresql+asyncpg://handle:handle-dev-password@localhost:5432/handle"
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect(("localhost", 5432))
    except OSError:
        pytest.skip("local postgres not reachable; run `docker compose up -d db migrate`")
    finally:
        s.close()
    return dsn
