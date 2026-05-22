"""Convenience entrypoint that runs fetch_dataset -> fetch_docs -> train_classifier -> ingest_corpus.

Run from the data-pipeline directory:
    GITHUB_TOKEN=<pat> uv run python -m src.run_all
"""

import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(step: str) -> None:
    log.info("=== %s ===", step)
    proc = subprocess.run(
        [sys.executable, "-m", f"src.{step}"],
        cwd=REPO_ROOT / "data-pipeline",
    )
    if proc.returncode != 0:
        log.error("step %s failed (exit %d)", step, proc.returncode)
        sys.exit(proc.returncode)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    _run("fetch_dataset")
    _run("fetch_docs")
    _run("train_classifier")
    _run("ingest_corpus")
    log.info("=== all stages done ===")


if __name__ == "__main__":
    main()
