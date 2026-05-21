"""Classification eval runner — golden-set evaluation + threshold check."""

import asyncio
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import yaml
from groq import AsyncGroq
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

LABELS = ["bug", "feature", "docs", "question"]
LABEL_TO_ID = {lbl: i for i, lbl in enumerate(LABELS)}


@dataclass
class ThresholdViolation:
    """One metric that fell below its threshold."""

    metric: str
    actual: float
    threshold: float


def load_thresholds(path: Path) -> dict[str, Any]:
    """Reads eval_thresholds.yaml from disk and returns the parsed dict."""
    with path.open("r") as f:
        return yaml.safe_load(f)


def check_classification_thresholds(
    thresholds: dict[str, Any], report: dict[str, Any]
) -> list[ThresholdViolation]:
    """Returns the list of violations against the roberta thresholds; [] means pass."""
    out: list[ThresholdViolation] = []
    cls = thresholds.get("classification", {}).get("roberta", {})
    metrics = report.get("models", {}).get("roberta", {})

    macro_min = cls.get("macro_f1_min")
    macro = metrics.get("macro_f1", 0.0)
    if macro_min is not None and macro < macro_min:
        out.append(ThresholdViolation(metric="macro_f1", actual=macro, threshold=macro_min))

    per_class_thresholds = cls.get("per_class_f1_min") or {}
    per_class_actual = metrics.get("per_class_f1") or {}
    for cls_name, threshold in per_class_thresholds.items():
        actual = per_class_actual.get(cls_name, 0.0)
        if actual < threshold:
            out.append(
                ThresholdViolation(
                    metric=f"per_class_f1.{cls_name}",
                    actual=actual,
                    threshold=threshold,
                )
            )

    return out


def _label_to_id(lbl: str) -> int:
    """Maps a label string to its index; -1 for unknown."""
    return LABEL_TO_ID.get(lbl, -1)


def load_golden_set(path: Path) -> list[dict[str, Any]]:
    """Reads the JSONL golden set into a list of dicts."""
    with path.open("r") as f:
        return [json.loads(line) for line in f if line.strip()]


async def classify_via_modelserver(
    client: httpx.AsyncClient, modelserver_url: str, text: str
) -> tuple[str | None, float]:
    """Calls modelserver /classify; returns (label, latency_ms)."""
    t0 = time.perf_counter()
    r = await client.post(f"{modelserver_url}/classify", json={"text": text}, timeout=30.0)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    if r.status_code >= 400:
        return None, elapsed_ms
    body = r.json()
    return body.get("label"), elapsed_ms


async def classify_via_llm(
    client: AsyncGroq, prompt_template: str, model: str, text: str
) -> tuple[str | None, float]:
    """Calls Groq with the few-shot prompt; returns (label, latency_ms)."""
    t0 = time.perf_counter()
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt_template.replace("{{ issue_text }}", text)}],
        max_tokens=16,
        temperature=0.0,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    raw = (resp.choices[0].message.content or "").strip().lower()
    m = re.search(r"\b(bug|feature|docs|question)\b", raw)
    return (m.group(1) if m else None), elapsed_ms


def _metrics(y_true: list[str], y_pred: list[str | None]) -> dict[str, Any]:
    """Computes accuracy, macro-F1, per-class F1, confusion matrix. Unknown preds -> wrong."""
    true_ids = [_label_to_id(t) for t in y_true]
    pred_ids = [_label_to_id(p or "unknown") for p in y_pred]

    # to avoid sklearn errors with -1 we map unknown preds to a dummy class 4
    pred_ids = [pid if pid != -1 else 4 for pid in pred_ids]

    macro_f1 = float(f1_score(true_ids, pred_ids, average="macro", labels=list(range(4))))
    per_class = f1_score(true_ids, pred_ids, average=None, labels=list(range(4)))
    per_class_dict = {LABELS[i]: float(per_class[i]) for i in range(4)}
    accuracy = float(accuracy_score(true_ids, pred_ids))
    cm = confusion_matrix(true_ids, pred_ids, labels=list(range(5))).tolist()

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class_f1": per_class_dict,
        "confusion_matrix": cm,
    }


async def run_classification_eval(
    golden_set_path: Path,
    modelserver_url: str,
    groq_client: AsyncGroq,
    llm_prompt_path: Path,
    llm_model: str = "llama-3.1-8b-instant",
) -> dict[str, Any]:
    """Runs both classifiers on the golden set and returns a structured report dict."""
    golden = load_golden_set(golden_set_path)
    truths = [g["true_label"] for g in golden]
    texts = [g["issue_text"] for g in golden]

    # ---- RoBERTa via modelserver ----
    rob_preds: list[str | None] = [None] * len(texts)
    rob_lat: list[float] = []
    async with httpx.AsyncClient() as http:
        sem = asyncio.Semaphore(5)

        async def one(i: int) -> None:
            async with sem:
                label, ms = await classify_via_modelserver(http, modelserver_url, texts[i])
                rob_preds[i] = label
                rob_lat.append(ms)

        await asyncio.gather(*[one(i) for i in range(len(texts))])

    # ---- LLM baseline via Groq ----
    prompt_template = llm_prompt_path.read_text()
    llm_preds: list[str | None] = [None] * len(texts)
    llm_lat: list[float] = []
    sem = asyncio.Semaphore(5)

    async def one_llm(i: int) -> None:
        async with sem:
            label, ms = await classify_via_llm(groq_client, prompt_template, llm_model, texts[i])
            llm_preds[i] = label
            llm_lat.append(ms)

    await asyncio.gather(*[one_llm(i) for i in range(len(texts))])

    rob_metrics = _metrics(truths, rob_preds)
    llm_metrics = _metrics(truths, llm_preds)

    return {
        "created_at": datetime.now(UTC).isoformat(),
        "n_golden": len(golden),
        "models": {
            "roberta": {
                **rob_metrics,
                "p50_latency_ms": float(np.percentile(rob_lat, 50)),
                "p95_latency_ms": float(np.percentile(rob_lat, 95)),
            },
            "llm_baseline": {
                **llm_metrics,
                "p50_latency_ms": float(np.percentile(llm_lat, 50)),
                "p95_latency_ms": float(np.percentile(llm_lat, 95)),
                "model": llm_model,
            },
        },
    }
