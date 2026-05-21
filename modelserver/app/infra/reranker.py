"""Cross-encoder reranker — loaded once at startup."""

from sentence_transformers import CrossEncoder

from app.infra.logging_setup import get_logger

log = get_logger(__name__)


def load_reranker(model_name: str) -> CrossEncoder:
    """Loads a CrossEncoder model. Heavy on first call (downloads weights)."""
    log.info("reranker.load.begin", model=model_name)
    enc = CrossEncoder(model_name)
    log.info("reranker.load.done")
    return enc


def rerank(
    enc: CrossEncoder, query: str, passages: list[str], top_k: int
) -> list[tuple[int, float]]:
    """Scores each passage against the query; returns top_k (idx, score) tuples sorted desc."""
    if not passages:
        return []
    pairs = [(query, p) for p in passages]
    scores = enc.predict(pairs)
    indexed = sorted(
        ((i, float(s)) for i, s in enumerate(scores)),
        key=lambda kv: -kv[1],
    )
    return indexed[:top_k]
