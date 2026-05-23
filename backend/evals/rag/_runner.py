"""RAG eval runner — retrieval + generation metrics + frozen-judge orchestration."""

import json
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from openai import AsyncAzureOpenAI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.schemas.rag import RagQuery
from app.services.rag.orchestrator import RagOrchestrator
from evals.rag._judge import judge_answer, load_judge_prompt
from evals.rag._kappa import compute_kappa


def compute_hit_at_k(retrieved_ids: list[str], truth_ids: list[str], k: int) -> float:
    """Returns 1.0 if any truth id appears in retrieved_ids[:k], else 0.0."""
    top = set(retrieved_ids[:k])
    return 1.0 if any(t in top for t in truth_ids) else 0.0


def compute_mrr_at_k(retrieved_ids: list[str], truth_ids: list[str], k: int) -> float:
    """Mean Reciprocal Rank — 1/rank of the first relevant item in top-k, else 0."""
    truth = set(truth_ids)
    for i, rid in enumerate(retrieved_ids[:k]):
        if rid in truth:
            return 1.0 / (i + 1)
    return 0.0


def _mean(values: Iterable[float]) -> float:
    """Helper: arithmetic mean; returns 0 for empty input."""
    lst = list(values)
    return sum(lst) / len(lst) if lst else 0.0


def load_golden_set(path: Path) -> list[dict[str, Any]]:
    """Reads the JSONL golden set as a list of dicts."""
    with path.open("r") as f:
        return [json.loads(line) for line in f if line.strip()]


def _build_context_text(hits: list[Any]) -> str:
    """Concatenates hits into a single context string for the judge."""
    return "\n\n---\n\n".join(f"[{h.source_path}]\n{h.text}" for h in hits)


async def _generate_answer(
    client: AsyncAzureOpenAI, model: str, question: str, context: str
) -> str:
    """Calls the LLM with a simple grounded-answer prompt; returns the answer text."""
    sys_prompt = (
        "You answer questions using only the provided context. "
        "If the context is insufficient, say so. Be concise."
    )
    user = f"Question: {question}\n\nContext:\n{context}\n\nAnswer:"
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user},
        ],
        max_tokens=400,
        temperature=0.0,
    )
    return (resp.choices[0].message.content or "").strip()


async def run_rag_eval(
    golden_set_path: Path,
    judge_prompt_path: Path,
    orchestrator: RagOrchestrator,
    session_factory: async_sessionmaker,
    llm: AsyncAzureOpenAI,
    llm_deployment: str,
) -> dict[str, Any]:
    """Runs retrieval + generation + judge for every golden triple, returns the report."""
    judge_model = llm_deployment
    answer_model = llm_deployment
    golden = load_golden_set(golden_set_path)
    judge_prompt = load_judge_prompt(judge_prompt_path)

    hits_at_5_list: list[float] = []
    mrr_at_10_list: list[float] = []
    faith_list: list[int] = []
    relev_list: list[int] = []
    human_scores_faith: list[int] = []
    human_scores_relev: list[int] = []
    judge_for_humans_faith: list[int] = []
    judge_for_humans_relev: list[int] = []
    per_example: list[dict[str, Any]] = []
    retrieval_latencies: list[float] = []

    for example in golden:
        question = example["question"]
        truth_ids = example["ground_truth_chunk_ids"]

        # ---- retrieve ----
        async with session_factory() as session:
            t0 = time.perf_counter()
            ctx = await orchestrator.search(session, RagQuery(question=question, top_k=10))
            retrieval_latencies.append((time.perf_counter() - t0) * 1000)

        retrieved_ids = [h.chunk_id for h in ctx.hits]
        hit5 = compute_hit_at_k(retrieved_ids, truth_ids, k=5)
        mrr = compute_mrr_at_k(retrieved_ids, truth_ids, k=10)
        hits_at_5_list.append(hit5)
        mrr_at_10_list.append(mrr)

        # ---- generate ----
        top5_hits = ctx.hits[:5]
        context_text = _build_context_text(top5_hits)
        candidate_answer = await _generate_answer(llm, answer_model, question, context_text)

        # ---- judge ----
        score = await judge_answer(
            llm,
            judge_prompt,
            judge_model,
            question=question,
            ideal_answer=example["ideal_answer"],
            context=context_text,
            candidate_answer=candidate_answer,
        )
        if score is not None:
            faith_list.append(score.faithfulness)
            relev_list.append(score.answer_relevancy)

        # ---- judge-human agreement (only for examples with a human_score) ----
        if "human_score" in example and score is not None:
            human_scores_faith.append(int(example["human_score"]["faithfulness"]))
            human_scores_relev.append(int(example["human_score"]["answer_relevancy"]))
            judge_for_humans_faith.append(score.faithfulness)
            judge_for_humans_relev.append(score.answer_relevancy)

        per_example.append(
            {
                "id": example["id"],
                "question": question,
                "hit_at_5": hit5,
                "mrr_at_10": mrr,
                "judge_faithfulness": score.faithfulness if score else None,
                "judge_answer_relevancy": score.answer_relevancy if score else None,
                "candidate_answer": candidate_answer[:400],
            }
        )

    # ---- aggregate ----
    kappa_faith = compute_kappa(human_scores_faith, judge_for_humans_faith)
    kappa_relev = compute_kappa(human_scores_relev, judge_for_humans_relev)
    kappa_avg = (
        (kappa_faith + kappa_relev) / 2 if (human_scores_faith or human_scores_relev) else 0.0
    )

    return {
        "created_at": datetime.now(UTC).isoformat(),
        "n_golden": len(golden),
        "retrieval": {
            "hit_at_5": _mean(hits_at_5_list),
            "mrr_at_10": _mean(mrr_at_10_list),
            "p50_latency_ms": float(np.percentile(retrieval_latencies, 50)),
            "p95_latency_ms": float(np.percentile(retrieval_latencies, 95)),
        },
        "generation": {
            "faithfulness": _mean(faith_list),
            "answer_relevancy": _mean(relev_list),
            "judge_model": judge_model,
            "answer_model": answer_model,
        },
        "judge": {
            "agreement_kappa": kappa_avg,
            "agreement_kappa_faithfulness": kappa_faith,
            "agreement_kappa_relevancy": kappa_relev,
            "n_human_labeled": len(human_scores_faith),
        },
        "per_example": per_example,
    }


def check_rag_thresholds(thresholds: dict[str, Any], report: dict[str, Any]) -> list[Any]:
    """Returns violations against rag thresholds; [] means pass."""
    from evals.classification._runner import ThresholdViolation

    out: list[ThresholdViolation] = []
    rt = thresholds.get("rag", {})

    # retrieval
    ret_t = rt.get("retrieval", {})
    ret_a = report.get("retrieval", {})
    for k in ("hit_at_5", "mrr_at_10"):
        thr = ret_t.get(f"{k}_min")
        actual = ret_a.get(k, 0.0)
        if thr is not None and actual < thr:
            out.append(ThresholdViolation(metric=f"retrieval.{k}", actual=actual, threshold=thr))

    # generation
    gen_t = rt.get("generation", {})
    gen_a = report.get("generation", {})
    for k in ("faithfulness", "answer_relevancy"):
        thr = gen_t.get(f"{k}_min")
        actual = gen_a.get(k, 0.0)
        if thr is not None and actual < thr:
            out.append(ThresholdViolation(metric=f"generation.{k}", actual=actual, threshold=thr))

    # judge agreement
    j_t = rt.get("judge", {})
    j_a = report.get("judge", {})
    thr = j_t.get("agreement_kappa_min")
    actual = j_a.get("agreement_kappa", 0.0)
    if thr is not None and actual < thr:
        out.append(ThresholdViolation(metric="judge.agreement_kappa", actual=actual, threshold=thr))

    return out
