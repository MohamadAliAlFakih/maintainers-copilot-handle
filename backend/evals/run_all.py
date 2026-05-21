"""Runs both evals and produces a combined eval_report.json for CI.

Returns non-zero if either eval fails its thresholds.
"""

import asyncio
import io
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402

log = get_logger(__name__)


async def _main() -> int:
    """Runs classification then RAG eval; combines their reports; uploads."""
    configure_logging()

    from evals.classification.run import _main as cls_main
    from evals.rag.run import _main as rag_main

    cls_code = await cls_main()
    rag_code = await rag_main()

    cls_path = Path("/app/evals/output/eval_report_classification.json")
    rag_path = Path("/app/evals/output/eval_report_rag.json")
    combined = {
        "classification": json.loads(cls_path.read_text()) if cls_path.exists() else None,
        "rag": json.loads(rag_path.read_text()) if rag_path.exists() else None,
    }

    out = Path("/app/evals/output/eval_report.json")
    out.write_text(json.dumps(combined, indent=2))

    settings = get_settings()
    sha = os.environ.get("GIT_COMMIT_SHA", "local-run")
    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )
    body = json.dumps(combined, indent=2).encode("utf-8")
    minio_client.put_object("evals", f"{sha}/eval_report.json", io.BytesIO(body), length=len(body))
    minio_client.put_object("evals", "latest/eval_report.json", io.BytesIO(body), length=len(body))

    final_code = max(cls_code or 0, rag_code or 0)
    log.info(
        "eval.run_all.done",
        classification_exit=cls_code,
        rag_exit=rag_code,
        final=final_code,
    )
    return final_code


def main() -> None:
    """CLI entry."""
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
