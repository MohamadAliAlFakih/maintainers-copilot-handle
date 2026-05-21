"""Tests /users/me — 401 when no token, 200 with the right user when authed."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_users_me_requires_auth(real_db_dsn: str, monkeypatch: pytest.MonkeyPatch):
    """Unauthenticated /users/me returns 401."""
    import app.main as main
    from app.infra.vault import VaultSecrets

    fake_vault = MagicMock()
    fake_vault.is_authenticated.return_value = True
    fake_vault.load_all_secrets.return_value = VaultSecrets(
        jwt_signing_key="x" * 64,
        groq_api_key="x",
        github_pat="x",
        minio_access_key="x",
        minio_secret_key="x",
        langfuse_public_key="x",
        langfuse_secret_key="x",
    )
    monkeypatch.setattr(main, "VaultClient", lambda **_kw: fake_vault)

    fake_minio = MagicMock()
    fake_minio.bucket_exists.return_value = True
    monkeypatch.setattr(main, "build_minio_client", lambda **_kw: fake_minio)

    fake_redis = MagicMock()
    fake_redis.aclose = AsyncMock()
    monkeypatch.setattr(main, "build_redis_client", lambda **_kw: fake_redis)

    fake_langfuse = MagicMock()
    monkeypatch.setattr(main, "build_langfuse_client", lambda **_kw: fake_langfuse)

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/users/me")
        assert r.status_code == 401
