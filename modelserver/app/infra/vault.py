"""Minimal Vault adapter for modelserver — fetches the secrets it needs at startup."""

from dataclasses import dataclass

import hvac


@dataclass(frozen=True)
class ModelserverSecrets:
    """All secrets modelserver requires at boot."""

    groq_api_key: str


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
        """Loads the Groq API key from secret/llm."""
        llm = self._client.secrets.kv.v2.read_secret_version(
            path="llm", mount_point="secret", raise_on_deleted_version=True
        )["data"]["data"]
        return ModelserverSecrets(groq_api_key=llm["groq_api_key"])
