"""Integration test — boots the FastAPI app with lifespan and hits /health."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    """Builds a TestClient that uses fake Vault/MinIO clients so lifespan succeeds."""
    import app.main as main
    from app.infra.vault import VaultSecrets

    fake_vault = MagicMock()
    fake_vault.is_authenticated.return_value = True
    fake_secrets = VaultSecrets(
        jwt_signing_key="x",
        groq_api_key="x",
        github_pat="x",
        minio_access_key="x",
        minio_secret_key="x",
        langfuse_public_key="x",
        langfuse_secret_key="x",
    )
    fake_vault.load_all_secrets.return_value = fake_secrets
    monkeypatch.setattr(main, "VaultClient", lambda **_kw: fake_vault)

    fake_minio = MagicMock()
    fake_minio.bucket_exists.return_value = True
    monkeypatch.setattr(main, "build_minio_client", lambda **_kw: fake_minio)

    fake_redis = MagicMock()
    fake_redis.aclose = AsyncMock()
    monkeypatch.setattr(main, "build_redis_client", lambda **_kw: fake_redis)

    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock()
    monkeypatch.setattr(main, "build_engine", lambda **_kw: fake_engine)
    monkeypatch.setattr(main, "build_session_factory", lambda *_a, **_kw: MagicMock())

    fake_langfuse = MagicMock()
    monkeypatch.setattr(main, "build_langfuse_client", lambda **_kw: fake_langfuse)

    with TestClient(main.app) as c:
        yield c


def test_health_returns_ok(client: TestClient):
    """The /health endpoint returns 200 and the expected JSON."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "api"}
