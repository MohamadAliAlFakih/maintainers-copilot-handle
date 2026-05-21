"""End-to-end auth flow against a real DB: register -> login -> /users/me -> logout."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_register_login_me_logout(real_db_dsn: str, monkeypatch: pytest.MonkeyPatch):
    """Full happy-path auth flow returns the expected status codes and user shape."""
    import app.main as main
    from app.infra.vault import VaultSecrets

    fake_vault = MagicMock()
    fake_vault.is_authenticated.return_value = True
    fake_vault.load_all_secrets.return_value = VaultSecrets(
        jwt_signing_key="x" * 64,  # not a placeholder; passes the check
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
        # register
        r = await client.post(
            "/auth/register",
            json={"email": "alice@example.com", "password": "supersecret123"},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["email"] == "alice@example.com"
        assert "hashed_password" not in body
        assert body["role"] == "user"

        # login
        r = await client.post(
            "/auth/jwt/login",
            data={"username": "alice@example.com", "password": "supersecret123"},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        assert token

        # /users/me
        r = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "alice@example.com"
        assert "hashed_password" not in body

        # bad token returns 401
        r = await client.get("/users/me", headers={"Authorization": "Bearer not-a-jwt"})
        assert r.status_code == 401

        # logout
        r = await client.post(
            "/auth/jwt/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 204
