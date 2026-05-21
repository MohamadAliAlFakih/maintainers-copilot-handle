"""Fetches fastapi/fastapi's docs/ folder via sparse-checkout, caches to MinIO.

Run inside backend:
    docker compose exec api uv run python /app/scripts/fetch_docs.py
"""

import io
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402

log = get_logger(__name__)

DOCS_PATH = "docs/en/docs"


def _sparse_checkout(
    target_dir: Path, repo: str = "https://github.com/fastapi/fastapi.git"
) -> Path:
    """Clones only docs/en/docs from fastapi/fastapi into target_dir. Returns docs path."""
    log.info("docs.fetch.clone", repo=repo)
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--sparse",
            repo,
            str(target_dir),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(target_dir), "sparse-checkout", "set", DOCS_PATH],
        check=True,
        capture_output=True,
    )
    docs = target_dir / DOCS_PATH
    if not docs.exists():
        alt = target_dir / "docs"
        if alt.exists():
            return alt
        raise RuntimeError(f"docs not found at {docs} or {alt}")
    return docs


def _tarball_docs(docs_dir: Path) -> bytes:
    """Packs the docs dir into a tar.gz and returns the bytes."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(str(docs_dir), arcname="docs")
    return buf.getvalue()


def main() -> None:
    """Clones the docs, tarballs them, and uploads to MinIO under corpus/raw/."""
    configure_logging()
    settings = get_settings()
    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )

    with tempfile.TemporaryDirectory() as tmp:
        docs_dir = _sparse_checkout(Path(tmp))
        md_files = list(docs_dir.rglob("*.md"))
        log.info("docs.fetch.collected", n_files=len(md_files))

        tar_bytes = _tarball_docs(docs_dir)

    minio_client.put_object(
        "corpus",
        "raw/fastapi_docs.tar.gz",
        io.BytesIO(tar_bytes),
        length=len(tar_bytes),
    )
    log.info("docs.fetch.uploaded", size_bytes=len(tar_bytes))


if __name__ == "__main__":
    main()
