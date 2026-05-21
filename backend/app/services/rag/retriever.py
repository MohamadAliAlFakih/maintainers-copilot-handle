"""RAG retriever: dense + sparse + RRF + rerank. RRF is a pure function for now."""

from dataclasses import dataclass


def rrf_combine(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion. Each list is ranked best-first. Returns merged list with scores.

    Score for item x = sum over each list it appears in of 1/(k + rank), where rank is 1-indexed.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for i, item in enumerate(ranked):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + i + 1)
    return sorted(scores.items(), key=lambda kv: -kv[1])


@dataclass
class RetrievedChunk:
    """A retrieved chunk row with its merged score and source-of-truth metadata."""

    chunk_id: str
    text: str
    source_type: str
    source_path: str
    section_headers: list[str]
    score: float
