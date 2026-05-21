"""Orchestrates chunk -> embed -> insert for one batch of source items."""

import io
import tarfile
from collections.abc import Iterable

import httpx
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.logging_setup import get_logger
from app.repositories.chunks import insert_chunk
from app.services.rag.chunker import Chunk, chunk_markdown
from scripts._chunker_issues import chunk_issue

log = get_logger(__name__)

# modelserver URL inside the docker network
MODELSERVER_URL = "http://modelserver:8001"


async def _embed_batch(
    client: httpx.AsyncClient, texts: list[str]
) -> tuple[list[list[float]], list[list[float]]]:
    """Calls modelserver /embed with both models. Returns (bge_list, minilm_list)."""
    r = await client.post(
        f"{MODELSERVER_URL}/embed",
        json={"texts": texts, "which": "both"},
        timeout=60.0,
    )
    r.raise_for_status()
    body = r.json()
    return body["bge"], body["minilm"]


def _docs_to_chunks(tarball_bytes: bytes) -> Iterable[Chunk]:
    """Extracts the docs tarball in-memory and yields Chunks for each .md file."""
    with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith(".md"):
                continue
            f = tar.extractfile(member)
            if f is None:
                continue
            md_text = f.read().decode("utf-8", errors="replace")
            yield from chunk_markdown(md_text, source_path=member.name)


def _issues_to_chunks(df: pd.DataFrame) -> Iterable[Chunk]:
    """Converts each row of the held-out RAG slice to issue chunks.

    Plan 1a's fetcher didn't pull comments, so for v1 we treat the body itself as the
    answer source. If RAG eval later shows weak answer-quality on issue questions, Plan
    2b's chunker call site can be swapped to pass a real `best_answer` field.
    """
    for row in df.itertuples(index=False):
        yield from chunk_issue(
            {
                "issue_number": int(row.issue_number),
                "title": row.title,
                "body": row.body,
                "best_answer": row.body,  # v1: body doubles as the answer source
            }
        )


async def ingest_all(
    session: AsyncSession,
    docs_tarball: bytes | None,
    issues_df: pd.DataFrame | None,
    batch_size: int = 32,
) -> int:
    """Runs the full ingest. Returns total chunks inserted."""
    chunks: list[Chunk] = []
    if docs_tarball is not None:
        chunks.extend(_docs_to_chunks(docs_tarball))
        log.info("ingest.docs_chunked", n=len(chunks))
    if issues_df is not None:
        before = len(chunks)
        chunks.extend(_issues_to_chunks(issues_df))
        log.info("ingest.issues_chunked", n=len(chunks) - before)

    total = 0
    async with httpx.AsyncClient() as http:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.text for c in batch]
            bge, mini = await _embed_batch(http, texts)

            for chunk, b, m in zip(batch, bge, mini, strict=True):
                await insert_chunk(session, chunk, b, m)

            total += len(batch)
            log.info("ingest.batch_done", done=total, total=len(chunks))

    await session.commit()
    return total
