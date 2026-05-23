"""CLI entrypoint: run classification eval against the live stack, write report.

Run inside backend:
    docker-compose exec api uv run python /app/evals/classification/run.py
"""

import asyncio
import io
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from openai import AsyncAzureOpenAI  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402
from app.infra.vault import VaultClient  # noqa: E402
from evals.classification._runner import (  # noqa: E402
    check_classification_thresholds,
    load_thresholds,
    run_classification_eval,
)

log = get_logger(__name__)

GOLDEN_PATH = Path("/app/evals/classification/golden_set.jsonl")
THRESHOLDS_PATH = Path("/app/evals/eval_thresholds.yaml")
LLM_PROMPT_PATH = Path("/app/prompts/classifier_llm.md")
OUTPUT_PATH = Path("/app/evals/output/eval_report_classification.json")


async def _main() -> int:
    """Returns 0 on success, 1 on threshold violation, 2 on missing config."""
    configure_logging()
    settings = get_settings()

    if not GOLDEN_PATH.exists():
        log.error("eval.refuse", reason=f"golden set missing at {GOLDEN_PATH}")
        return 2

    vault = VaultClient(addr=settings.vault_addr, token=settings.vault_root_token)
    secrets = vault.load_all_secrets()
    if "placeholder" in secrets.llm_api_key:
        log.error("eval.refuse", reason="llm api key is placeholder")
        return 2

    llm = AsyncAzureOpenAI(
        api_key=secrets.llm_api_key,
        azure_endpoint=secrets.llm_endpoint,
        api_version=secrets.llm_api_version,
        timeout=60.0,
    )

    log.info("eval.classification.begin")
    report = await run_classification_eval(
        golden_set_path=GOLDEN_PATH,
        modelserver_url="http://modelserver:8001",
        llm_client=llm,
        llm_deployment=secrets.llm_deployment,
        llm_prompt_path=LLM_PROMPT_PATH,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2))
    log.info("eval.classification.report_written", path=str(OUTPUT_PATH))

    # ---- upload to MinIO ----
    sha = os.environ.get("GIT_COMMIT_SHA", "local-run")
    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )
    body = json.dumps(report, indent=2).encode("utf-8")
    minio_client.put_object(
        "evals", f"{sha}/classification_report.json", io.BytesIO(body), length=len(body)
    )
    minio_client.put_object(
        "evals", "latest/classification_report.json", io.BytesIO(body), length=len(body)
    )

    # ---- threshold check ----
    thresholds = load_thresholds(THRESHOLDS_PATH)
    violations = check_classification_thresholds(thresholds, report)

    if violations:
        log.error(
            "eval.classification.threshold_violations",
            violations=[
                {"metric": v.metric, "actual": v.actual, "threshold": v.threshold}
                for v in violations
            ],
        )
        for v in violations:
            print(f"[FAIL] {v.metric}: {v.actual:.4f} < {v.threshold:.4f}", file=sys.stderr)
        await llm.close()
        return 1

    print(
        f"[PASS] classification — roberta macro_f1={report['models']['roberta']['macro_f1']:.4f} "
        f"(threshold {thresholds['classification']['roberta']['macro_f1_min']:.4f})"
    )
    await llm.close()
    return 0


def main() -> None:
    """CLI entry; sys.exits with the runner's return code."""
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
