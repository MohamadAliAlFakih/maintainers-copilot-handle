"""Thin async client for talking to the modelserver."""

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

MODELSERVER_URL = "http://modelserver:8001"


async def _retry_post(
    client: httpx.AsyncClient, url: str, json_body: dict, timeout: float = 60.0
) -> dict:
    """POST with 3 retries on transient errors. Raises on non-2xx after final attempt."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    ):
        with attempt:
            r = await client.post(url, json=json_body, timeout=timeout)
            r.raise_for_status()
            return r.json()
    return {}


async def embed_texts(
    client: httpx.AsyncClient, texts: list[str], which: str = "bge"
) -> list[list[float]]:
    """Calls modelserver /embed; returns list of embeddings for the chosen model."""
    body = await _retry_post(client, f"{MODELSERVER_URL}/embed", {"texts": texts, "which": which})
    return body["bge"] if which == "bge" else body["minilm"]


async def rerank_passages(
    client: httpx.AsyncClient, query: str, passages: list[str], top_k: int = 5
) -> list[tuple[int, float]]:
    """Calls modelserver /rerank; returns top_k (passage_index, score) tuples."""
    body = await _retry_post(
        client,
        f"{MODELSERVER_URL}/rerank",
        {"query": query, "passages": passages, "top_k": top_k},
    )
    return [(h["index"], h["score"]) for h in body["hits"]]
