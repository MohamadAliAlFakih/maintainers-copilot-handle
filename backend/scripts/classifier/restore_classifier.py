"""Restore the trained classifier artifacts from the host-mounted disk to MinIO.

Use this when MinIO has been wiped (e.g. `docker compose down -v`) but the
`./classifier_data/` host volume still has the trained model weights, card, and
eval report on disk; running this rebuilds the `models/classifier/<MODEL_NAME>/`
keys in ~30s, avoiding a full retrain.

Run inside the api container:
    docker compose run --rm api uv run python /app/scripts/classifier/restore_classifier.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402

log = get_logger(__name__)

MODEL_NAME = "roberta-issue-cls-v1"
HOST_DIR = Path("/data/classifier_artifacts") / MODEL_NAME

REQUIRED_FILES = ("model.safetensors", "model_card.md", "eval_report.json")


def main() -> None:
    """Idempotently re-uploads the three artifacts from host disk to MinIO.

    No-ops if MinIO already has them (so it's safe to run on every boot).
    No-ops if the host dir doesn't exist either (fresh checkout, no training yet).
    """
    configure_logging()
    settings = get_settings()

    if not HOST_DIR.exists():
        log.info("restore.skip", reason=f"host dir {HOST_DIR} not present; nothing to restore")
        return

    missing = [name for name in REQUIRED_FILES if not (HOST_DIR / name).exists()]
    if missing:
        log.info("restore.skip", reason=f"host dir incomplete (missing: {missing})")
        return

    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )

    prefix = f"classifier/{MODEL_NAME}"

    # Skip upload if MinIO already has all three required keys.
    from minio.error import S3Error

    try:
        for name in REQUIRED_FILES:
            minio_client.stat_object("models", f"{prefix}/{name}")
        log.info("restore.skip", reason="MinIO already has all artifacts")
        return
    except S3Error:
        log.info("restore.minio_missing", action="re-uploading from host disk")

    from io import BytesIO

    for name in REQUIRED_FILES:
        path = HOST_DIR / name
        data = path.read_bytes()
        key = f"{prefix}/{name}"
        minio_client.put_object("models", key, BytesIO(data), length=len(data))
        log.info("restore.uploaded", key=key, bytes=len(data))

    log.info("restore.done", model=MODEL_NAME)


if __name__ == "__main__":
    main()
