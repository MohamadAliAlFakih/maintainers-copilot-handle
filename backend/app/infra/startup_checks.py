"""Refuse-to-boot policy — aborts the process on any missing/misconfigured dependency."""

from pathlib import Path

from minio import Minio

from app.config import Settings
from app.infra.logging_setup import get_logger
from app.infra.minio import REQUIRED_BUCKETS, assert_buckets_exist
from app.infra.vault import VaultClient

log = get_logger(__name__)

REQUIRED_PROMPTS = (
    "chatbot_system",
    "classifier_llm",
    "rag_answer",
    "hyde_generate",
    "rag_judge",
    "conversation_summary",
)


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


async def check_chunks_not_empty(session_factory) -> None:  # type: ignore[no-untyped-def]
    """Refuses to boot if the chunks table is empty (RAG would silently return nothing)."""
    from app.repositories.chunks import count_chunks

    async with session_factory() as session:
        n = await count_chunks(session)
        if n == 0:
            raise StartupFailure(
                "chunks table is empty. Run scripts/ingest_corpus.py before booting the api."
            )


def check_required_prompts(prompts_dir: Path) -> None:
    """Refuses to boot if any required prompt file is missing."""
    missing: list[str] = []
    for name in REQUIRED_PROMPTS:
        if not (prompts_dir / f"{name}.md").exists():
            missing.append(name)
    if missing:
        raise StartupFailure(f"missing required prompt files in {prompts_dir}: {missing}")


def check_eval_thresholds(thresholds_path: Path) -> None:
    """Refuses to boot if eval_thresholds.yaml has any value of 0 or null."""
    import yaml

    if not thresholds_path.exists():
        raise StartupFailure(f"eval_thresholds.yaml missing at {thresholds_path}")

    data = yaml.safe_load(thresholds_path.read_text(encoding="utf-8"))

    def _walk(node, path: str) -> None:  # type: ignore[no-untyped-def]
        if isinstance(node, dict):
            for k, v in node.items():
                _walk(v, f"{path}.{k}")
        elif isinstance(node, (int, float)):
            if node == 0:
                raise StartupFailure(f"eval threshold is zero at {path}")
        elif node is None:
            raise StartupFailure(f"eval threshold is null at {path}")

    _walk(data, "")


def run_all_checks(
    settings: Settings,
    vault: VaultClient,
    minio_client: Minio,
    jwt_signing_key: str,
    prompts_dir: Path | None = None,
    thresholds_path: Path | None = None,
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
    if prompts_dir is not None:
        check_required_prompts(prompts_dir)
        log.info("startup.checks.prompts_ok")
    if thresholds_path is not None:
        check_eval_thresholds(thresholds_path)
        log.info("startup.checks.thresholds_ok")
    log.info("startup.checks.done")
