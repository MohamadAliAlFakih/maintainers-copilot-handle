"""CLI entrypoint: run RAG eval against the live stack, write report, gate.

Run inside backend:
    docker-compose exec api uv run python /app/evals/rag/run.py
"""

import asyncio
import io
import json
import os
import sys
from pathlib import Path

import httpx
from groq import AsyncGroq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.db import build_engine, build_session_factory  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402
from app.infra.vault import VaultClient  # noqa: E402
from app.services.rag.orchestrator import RagOrchestrator  # noqa: E402
from evals.classification._runner import load_thresholds  # noqa: E402
from evals.rag._runner import check_rag_thresholds, run_rag_eval  # noqa: E402

log = get_logger(__name__)

GOLDEN = Path("/app/evals/rag/golden_set.jsonl")
THRESHOLDS = Path("/app/evals/eval_thresholds.yaml")
JUDGE_PROMPT = Path("/app/prompts/rag_judge.md")
OUTPUT = Path("/app/evals/output/eval_report_rag.json")


async def _main() -> int:
    """Returns 0 on pass, 1 on threshold violation, 2 on missing config."""
    configure_logging()
    settings = get_settings()

    if not GOLDEN.exists():
        log.error("rag_eval.refuse", reason=f"golden set missing at {GOLDEN}")
        return 2

    vault = VaultClient(addr=settings.vault_addr, token=settings.vault_root_token)
    secrets = vault.load_all_secrets()
    if "placeholder" in secrets.groq_api_key:
        log.error("rag_eval.refuse", reason="groq key is placeholder")
        return 2

    groq = AsyncGroq(api_key=secrets.groq_api_key, timeout=60.0)
    http = httpx.AsyncClient(timeout=60.0)
    engine = build_engine(settings.db_dsn)
    factory = build_session_factory(engine)

    orchestrator = RagOrchestrator(
        groq=groq,
        groq_model_cheap="llama-3.1-8b-instant",
        prompts_dir=Path("/app/prompts"),
        modelserver_http=http,
    )

    log.info("rag_eval.begin")
    report = await run_rag_eval(GOLDEN, JUDGE_PROMPT, orchestrator, factory, groq)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2))
    log.info("rag_eval.report_written", path=str(OUTPUT))

    sha = os.environ.get("GIT_COMMIT_SHA", "local-run")
    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )
    body = json.dumps(report, indent=2).encode("utf-8")
    minio_client.put_object("evals", f"{sha}/rag_report.json", io.BytesIO(body), length=len(body))
    minio_client.put_object("evals", "latest/rag_report.json", io.BytesIO(body), length=len(body))

    thresholds = load_thresholds(THRESHOLDS)
    violations = check_rag_thresholds(thresholds, report)

    await http.aclose()
    await groq.close()
    await engine.dispose()

    if violations:
        for v in violations:
            print(f"[FAIL] {v.metric}: {v.actual:.4f} < {v.threshold:.4f}", file=sys.stderr)
        return 1

    print(
        f"[PASS] rag — hit@5={report['retrieval']['hit_at_5']:.3f} "
        f"mrr@10={report['retrieval']['mrr_at_10']:.3f} "
        f"faith={report['generation']['faithfulness']:.2f} "
        f"relev={report['generation']['answer_relevancy']:.2f} "
        f"kappa={report['judge']['agreement_kappa']:.2f}"
    )
    return 0


def main() -> None:
    """CLI entry."""
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
