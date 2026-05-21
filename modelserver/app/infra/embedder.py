"""Loads BGE-small + MiniLM at startup; provides batched embed function."""

from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer

from app.infra.logging_setup import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class LoadedEmbedders:
    """Both embedding models loaded once per process."""

    bge: SentenceTransformer
    minilm: SentenceTransformer


def load_embedders(primary_name: str, challenger_name: str) -> LoadedEmbedders:
    """Downloads + loads both models. Heavy — only called once in lifespan."""
    log.info("embedders.load.begin", primary=primary_name, challenger=challenger_name)
    bge = SentenceTransformer(primary_name)
    minilm = SentenceTransformer(challenger_name)
    log.info("embedders.load.done")
    return LoadedEmbedders(bge=bge, minilm=minilm)


def embed_batch(embedder: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    """Embeds a list of strings; returns list of float lists (JSON-safe)."""
    if not texts:
        return []
    arr = embedder.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    return [row.tolist() for row in arr]
