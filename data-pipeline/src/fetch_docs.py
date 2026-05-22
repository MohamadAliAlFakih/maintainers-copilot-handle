"""Sparse-checkout pandas-dev/pandas's doc/source/ folder; tarball it to data/raw/docs/.

Run from the data-pipeline directory:
    uv run python -m src.fetch_docs
"""

import argparse
import io
import logging
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "data" / "raw" / "docs"

DOCS_PATH = "doc/source"
DEFAULT_REPO = "https://github.com/pandas-dev/pandas.git"


def _sparse_checkout(target_dir: Path, repo: str = DEFAULT_REPO) -> Path:
    log.info("cloning %s (sparse)", repo)
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
        raise RuntimeError(f"docs not found at {docs}")
    return docs


def _tarball_docs(docs_dir: Path) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(str(docs_dir), arcname="docs")
    return buf.getvalue()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    tar_path = args.out / "pandas_docs.tar.gz"
    if tar_path.exists() and not args.force:
        log.info("skip: %s already exists (use --force to overwrite)", tar_path)
        sys.exit(0)

    with tempfile.TemporaryDirectory() as tmp:
        docs_dir = _sparse_checkout(Path(tmp))
        files = list(docs_dir.rglob("*"))
        log.info("collected %d files", sum(1 for f in files if f.is_file()))
        tar_bytes = _tarball_docs(docs_dir)

    tar_path.write_bytes(tar_bytes)
    log.info("wrote %s (%d bytes)", tar_path, len(tar_bytes))


if __name__ == "__main__":
    main()
