"""Computes hit@5 / MRR@10 for dense-only, sparse-only, RRF, and BGE vs MiniLM.

Run inside backend:
    docker-compose exec api uv run python /app/evals/rag/_retrieval_ablation.py
"""

import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings  # noqa: E402
from app.infra.db import build_engine, build_session_factory  # noqa: E402
from app.infra.modelserver_client import embed_texts  # noqa: E402
from app.repositories.chunks import dense_search, sparse_search  # noqa: E402
from app.services.rag.retriever import rrf_combine  # noqa: E402
from evals.rag._runner import compute_hit_at_k, compute_mrr_at_k, load_golden_set  # noqa: E402

GOLDEN = Path("/app/evals/rag/golden_set.jsonl")


async def _eval_one_variant(session, http, golden, embedder: str, variant: str) -> dict:
    """Runs one (embedder, variant) combination across the golden set."""
    hits = []
    mrrs = []
    for ex in golden:
        q = ex["question"]
        truth = ex["ground_truth_chunk_ids"]

        dense_ids: list[str] = []
        sparse_ids: list[str] = []

        if variant in ("dense", "rrf"):
            emb_list = await embed_texts(http, [q], which=embedder)
            emb = emb_list[0]
            dense = await dense_search(session, emb, embedder=embedder, top_k=50)
            dense_ids = [c for c, _s in dense]
        if variant in ("sparse", "rrf"):
            sparse = await sparse_search(session, q, top_k=50)
            sparse_ids = [c for c, _s in sparse]

        if variant == "dense":
            ids = dense_ids
        elif variant == "sparse":
            ids = sparse_ids
        else:  # rrf
            merged = rrf_combine([dense_ids, sparse_ids], k=60)
            ids = [c for c, _s in merged]

        hits.append(compute_hit_at_k(ids, truth, k=5))
        mrrs.append(compute_mrr_at_k(ids, truth, k=10))

    return {
        "embedder": embedder,
        "variant": variant,
        "hit_at_5": sum(hits) / len(hits),
        "mrr_at_10": sum(mrrs) / len(mrrs),
    }


async def main() -> None:
    """Runs all variants and prints a markdown table for DECISIONS.md."""
    settings = get_settings()
    engine = build_engine(settings.db_dsn)
    factory = build_session_factory(engine)
    golden = load_golden_set(GOLDEN)

    results = []
    async with httpx.AsyncClient(timeout=60.0) as http:
        async with factory() as session:
            for embedder in ("bge", "minilm"):
                for variant in ("dense", "sparse", "rrf"):
                    if variant == "sparse" and embedder == "minilm":
                        continue  # sparse is embedder-independent; only run once
                    r = await _eval_one_variant(session, http, golden, embedder, variant)
                    results.append(r)
                    print(
                        f"  {embedder}/{variant}: "
                        f"hit@5={r['hit_at_5']:.3f} mrr@10={r['mrr_at_10']:.3f}"
                    )

    print("\n\n### Retrieval ablation\n")
    print("| Embedder | Variant | hit@5 | MRR@10 |")
    print("|---|---|---|---|")
    for r in results:
        print(f"| {r['embedder']} | {r['variant']} | {r['hit_at_5']:.3f} | {r['mrr_at_10']:.3f} |")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
