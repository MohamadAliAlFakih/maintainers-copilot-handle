"""Refuse-to-boot policy — aborts the process on any missing/misconfigured dependency."""

from minio import Minio

from app.config import Settings
from app.infra.logging_setup import get_logger
from app.infra.minio import REQUIRED_BUCKETS, assert_buckets_exist
from app.infra.vault import VaultClient

log = get_logger(__name__)


class StartupFailure(Exception):
    """Raised when a refuse-to-boot check fails. Caller exits the process."""


def check_settings_sanity(settings: Settings) -> None:
    """Validates settings beyond what Pydantic catches (e.g., whitespace tokens)."""
    if not settings.vault_root_token.strip():
        raise StartupFailure("settings.vault_root_token is blank or whitespace-only")
    if not settings.db_password.strip():
        raise StartupFailure("settings.db_password is blank or whitespace-only")


def check_vault_reachable(vault: VaultClient) -> None:
    """Confirms we can talk to Vault and our token works."""
    if not vault.is_authenticated():
        raise StartupFailure(
            "Vault is unreachable or root token is invalid. Check VAULT_ADDR and VAULT_ROOT_TOKEN."
        )


def check_minio_buckets(client: Minio) -> None:
    """All required MinIO buckets must exist before boot continues."""
    missing = assert_buckets_exist(client)
    if missing:
        raise StartupFailure(
            f"MinIO is missing required buckets: {missing}. "
            f"Expected: {list(REQUIRED_BUCKETS)}. "
            "Did the minio-init container run?"
        )


def check_jwt_signing_key(signing_key: str) -> None:
    """Refuses to boot if the JWT signing key is the dev placeholder."""
    if not signing_key or "placeholder" in signing_key:
        raise StartupFailure(
            "JWT signing key is missing or still the placeholder. "
            "Run scripts/rotate_jwt_key.sh (or `vault kv put secret/jwt signing_key=<long-random>`)."
        )


def run_all_checks(
    settings: Settings,
    vault: VaultClient,
    minio_client: Minio,
    jwt_signing_key: str,
) -> None:
    """Runs every refuse-to-boot check in order and logs progress."""
    log.info("startup.checks.begin")
    check_settings_sanity(settings)
    log.info("startup.checks.settings_ok")
    check_vault_reachable(vault)
    log.info("startup.checks.vault_ok")
    check_minio_buckets(minio_client)
    log.info("startup.checks.minio_ok")
    check_jwt_signing_key(jwt_signing_key)
    log.info("startup.checks.jwt_ok")
    log.info("startup.checks.done")
