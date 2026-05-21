"""Offline LLM baseline eval — runs llama-3.1-8b-instant on the test split, writes report.

Run inside backend container:
    docker compose exec api uv run python /app/scripts/eval_llm_baseline.py
"""

import asyncio
import io
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from groq import AsyncGroq
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.logging_setup import configure_logging, get_logger  # noqa: E402
from app.infra.minio import build_minio_client  # noqa: E402
from app.infra.vault import VaultClient  # noqa: E402

log = get_logger(__name__)


async def _classify_one(
    client: AsyncGroq, model: str, text: str, prompt_template: str
) -> tuple[str | None, float]:
    """Calls Groq once and parses the result; returns (label, latency_ms)."""
    t0 = time.perf_counter()
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt_template.replace("{{ issue_text }}", text)}],
        max_tokens=16,
        temperature=0.0,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    raw = (resp.choices[0].message.content or "").strip().lower()

    words = re.findall(r"[a-z]+", raw)
    label: str | None = words[-1] if words else None
    if label not in {"bug", "feature", "docs", "question"}:
        label = None
    return label, elapsed_ms


async def _main() -> None:
    """Pulls test split, runs LLM, writes eval_report to MinIO."""
    configure_logging()
    settings = get_settings()

    # ---- secrets ----
    vault = VaultClient(addr=settings.vault_addr, token=settings.vault_root_token)
    secrets = vault.load_all_secrets()
    if "placeholder" in secrets.groq_api_key:
        log.error("eval_llm.refuse", reason="groq key is placeholder")
        sys.exit(1)

    # ---- minio ----
    minio_client = build_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )

    # ---- pull test split ----
    resp = minio_client.get_object("dataset", "splits/test.parquet")
    try:
        test_df = pd.read_parquet(io.BytesIO(resp.read()))
    finally:
        resp.close()
        resp.release_conn()
    log.info("eval_llm.loaded_test", n=len(test_df))

    # ---- load prompt from disk ----
    prompt_path = Path("/app/prompts/classifier_llm.md")
    if not prompt_path.exists():
        log.error("eval_llm.refuse", reason=f"prompt file missing at {prompt_path}")
        sys.exit(1)
    prompt_template = prompt_path.read_text()

    # ---- build groq client ----
    client = AsyncGroq(api_key=secrets.groq_api_key, timeout=60.0)

    # ---- run with a small concurrency limit to be polite ----
    sem = asyncio.Semaphore(5)
    preds: list[str | None] = [None] * len(test_df)
    latencies: list[float] = []

    async def _bounded(idx: int, text: str) -> None:
        async with sem:
            label, ms = await _classify_one(client, "llama-3.1-8b-instant", text, prompt_template)
            preds[idx] = label
            latencies.append(ms)
            if idx % 50 == 0:
                log.info("eval_llm.progress", done=idx, total=len(test_df))

    tasks = [
        _bounded(i, f"{row.title}\n\n{row.body}")
        for i, row in enumerate(test_df.itertuples(index=False))
    ]
    await asyncio.gather(*tasks)

    # ---- compute metrics ----
    LABELS = ["bug", "feature", "docs", "question"]
    truth = test_df["class"].tolist()
    cleaned_preds = [p if p in LABELS else "unknown" for p in preds]

    label_to_id = {lbl: i for i, lbl in enumerate(LABELS)}
    label_to_id["unknown"] = 4

    y_true = [label_to_id[t] for t in truth]
    y_pred = [label_to_id[p] for p in cleaned_preds]

    accuracy = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", labels=list(range(4))))
    per_class = f1_score(y_true, y_pred, average=None, labels=list(range(4)))
    per_class_dict = {LABELS[i]: float(per_class[i]) for i in range(4)}
    cm = confusion_matrix(y_true, y_pred, labels=list(range(5))).tolist()

    n_unknown = sum(1 for p in preds if p is None)

    report = {
        "model": "llama-3.1-8b-instant",
        "n_test": len(test_df),
        "n_unparseable": n_unknown,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class_f1": per_class_dict,
        "confusion_matrix": cm,
        "p50_latency_ms": float(np.percentile(latencies, 50)),
        "p95_latency_ms": float(np.percentile(latencies, 95)),
    }

    out_bytes = json.dumps(report, indent=2).encode("utf-8")
    minio_client.put_object(
        "models",
        "classifier_llm_baseline/eval_report.json",
        io.BytesIO(out_bytes),
        length=len(out_bytes),
    )
    log.info("eval_llm.done", macro_f1=macro_f1, accuracy=accuracy, unknown=n_unknown)
    print(json.dumps(report, indent=2))

    await client.close()


def main() -> None:
    """CLI entrypoint."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
