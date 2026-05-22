"""SQL operations on the chunks table — count, dense + sparse search.

Inserts are handled by the offline data-pipeline + the online artifacts-loader
(raw SQL bulk-insert). This module is read-only for the online stack.
"""

from typing import Literal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.models import Chunk as ChunkORM


async def count_chunks(session: AsyncSession) -> int:
    """Returns the total number of chunks; used by refuse-to-boot check."""
    result = await session.execute(select(func.count(ChunkORM.id)))
    return result.scalar_one()


async def delete_all_chunks(session: AsyncSession) -> int:
    """Wipes the chunks table — used by re-ingest to ensure idempotency."""
    result = await session.execute(text("DELETE FROM chunks"))
    return result.rowcount or 0


async def dense_search(
    session: AsyncSession,
    query_embedding: list[float],
    embedder: Literal["bge", "minilm"] = "bge",
    top_k: int = 50,
    source_type: str | None = None,
) -> list[tuple[str, float]]:
    """Returns top-k chunk_ids sorted by cosine similarity to the query embedding.

    Score is `1 - cosine_distance` so higher = more similar.
    """
    column = "embedding_bge" if embedder == "bge" else "embedding_minilm"
    where_clause = ""
    # pgvector via asyncpg expects the vector as a string literal "[v1,v2,...]"
    emb_literal = "[" + ",".join(repr(float(x)) for x in query_embedding) + "]"
    params: dict = {"emb": emb_literal, "top_k": top_k}
    if source_type is not None:
        where_clause = "WHERE source_type = :source_type"
        params["source_type"] = source_type

    sql = text(
        f"""
        SELECT chunk_id, 1 - ({column} <=> CAST(:emb AS vector)) AS score
        FROM chunks
        {where_clause}
        ORDER BY {column} <=> CAST(:emb AS vector)
        LIMIT :top_k
        """
    )
    result = await session.execute(sql, params)
    return [(row.chunk_id, float(row.score)) for row in result.all()]


async def sparse_search(
    session: AsyncSession,
    query: str,
    top_k: int = 50,
    source_type: str | None = None,
) -> list[tuple[str, float]]:
    """Returns top-k chunk_ids sorted by Postgres FTS ts_rank_cd against `tsv`."""
    where_clause = ""
    params: dict = {"q": query, "top_k": top_k}
    if source_type is not None:
        where_clause = "AND source_type = :source_type"
        params["source_type"] = source_type

    sql = text(
        f"""
        SELECT chunk_id, ts_rank_cd(tsv, plainto_tsquery('english', :q)) AS score
        FROM chunks
        WHERE tsv @@ plainto_tsquery('english', :q)
        {where_clause}
        ORDER BY score DESC
        LIMIT :top_k
        """
    )
    result = await session.execute(sql, params)
    return [(row.chunk_id, float(row.score)) for row in result.all()]


async def get_chunks_by_ids(session: AsyncSession, chunk_ids: list[str]) -> dict[str, ChunkORM]:
    """Bulk-loads chunk rows by chunk_id; returns dict keyed by chunk_id."""
    if not chunk_ids:
        return {}
    result = await session.execute(select(ChunkORM).where(ChunkORM.chunk_id.in_(chunk_ids)))
    return {row.chunk_id: row for row in result.scalars()}
