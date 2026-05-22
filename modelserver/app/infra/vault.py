"""Minimal Vault adapter for modelserver — fetches the secrets it needs at startup."""

from dataclasses import dataclass

import hvac


@dataclass(frozen=True)
class ModelserverSecrets:
    """All secrets modelserver requires at boot."""

    llm_api_key: str
    llm_endpoint: str
    llm_deployment: str
    llm_api_version: str


class VaultClient:
    """Tiny Vault wrapper just for modelserver's needs."""

    def __init__(self, addr: str, token: str) -> None:
        self._client = hvac.Client(url=addr, token=token)

    def is_authenticated(self) -> bool:
        """Returns True iff Vault is reachable and the token is valid."""
        try:
            return self._client.is_authenticated()
        except Exception:  # noqa: BLE001
            return False

    def load_secrets(self) -> ModelserverSecrets:
        """Loads the Azure OpenAI credentials from secret/llm."""
        llm = self._client.secrets.kv.v2.read_secret_version(
            path="llm", mount_point="secret", raise_on_deleted_version=True
        )["data"]["data"]
        return ModelserverSecrets(
            llm_api_key=llm["api_key"],
            llm_endpoint=llm["endpoint"],
            llm_deployment=llm["deployment"],
            llm_api_version=llm.get("api_version", "2024-02-01"),
        )
