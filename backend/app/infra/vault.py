"""Vault client wrapper — fetches secrets at startup; refuse-to-boot on failure."""

from dataclasses import dataclass

import hvac

from app.infra.logging_setup import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class VaultSecrets:
    """Snapshot of all secrets fetched at startup. Immutable on purpose."""

    jwt_signing_key: str
    llm_api_key: str
    llm_endpoint: str
    llm_deployment: str
    llm_api_version: str
    github_pat: str
    minio_access_key: str
    minio_secret_key: str
    langfuse_public_key: str
    langfuse_secret_key: str


class VaultClient:
    """Synchronous Vault client used only during lifespan startup."""

    def __init__(self, addr: str, token: str) -> None:
        self._client = hvac.Client(url=addr, token=token)

    def is_authenticated(self) -> bool:
        """Returns True when we can talk to Vault and the token is valid."""
        try:
            return self._client.is_authenticated()
        except Exception as e:  # noqa: BLE001 — startup check should not crash
            log.error("vault.auth_check_failed", error=str(e))
            return False

    def read_kv(self, path: str) -> dict[str, str]:
        """Reads a kv-v2 secret at `secret/<path>` and returns the data dict."""
        resp = self._client.secrets.kv.v2.read_secret_version(
            path=path, mount_point="secret", raise_on_deleted_version=True
        )
        return resp["data"]["data"]

    def load_all_secrets(self) -> VaultSecrets:
        """Reads all required secrets and packages them into a VaultSecrets snapshot."""
        jwt = self.read_kv("jwt")
        llm = self.read_kv("llm")
        gh = self.read_kv("github")
        minio = self.read_kv("minio")
        langfuse = self.read_kv("langfuse")

        return VaultSecrets(
            jwt_signing_key=jwt["signing_key"],
            llm_api_key=llm["api_key"],
            llm_endpoint=llm["endpoint"],
            llm_deployment=llm["deployment"],
            llm_api_version=llm.get("api_version", "2024-02-01"),
            github_pat=gh["personal_access_token"],
            minio_access_key=minio["access_key"],
            minio_secret_key=minio["secret_key"],
            langfuse_public_key=langfuse["public_key"],
            langfuse_secret_key=langfuse["secret_key"],
        )
