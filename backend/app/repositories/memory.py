"""SQL for long_term_memory — insert + cosine-similarity search."""

import uuid

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory.models import LongTermMemory


def _to_vector_literal(embedding: list[float]) -> str:
    """asyncpg + pgvector needs the vector cast from a string literal, not a list."""
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


async def insert_fact(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    fact_text: str,
    embedding: list[float],
    source_message_id: uuid.UUID | None = None,
) -> LongTermMemory:
    """Adds a new fact row; caller commits the surrounding transaction."""
    row = LongTermMemory(
        user_id=user_id,
        fact_text=fact_text,
        embedding=embedding,
        source_message_id=source_message_id,
    )
    session.add(row)
    await session.flush()
    return row


async def search_facts(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[tuple[str, float]]:
    """Returns top-k (fact_text, similarity) tuples for this user."""
    emb_literal = _to_vector_literal(query_embedding)
    sql = text(
        """
        SELECT fact_text, 1 - (embedding <=> CAST(:emb AS vector)) AS score
        FROM long_term_memory
        WHERE user_id = :uid
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT :top_k
        """
    )
    result = await session.execute(sql, {"uid": user_id, "emb": emb_literal, "top_k": top_k})
    return [(row.fact_text, float(row.score)) for row in result.all()]


async def list_facts_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[LongTermMemory]:
    """Returns all of a user's facts ordered by created_at desc (for the inspector UI)."""
    result = await session.execute(
        select(LongTermMemory)
        .where(LongTermMemory.user_id == user_id)
        .order_by(LongTermMemory.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_fact(session: AsyncSession, fact_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Deletes a fact if it belongs to the user. Returns True on delete."""
    result = await session.execute(
        delete(LongTermMemory).where(
            LongTermMemory.id == fact_id, LongTermMemory.user_id == user_id
        )
    )
    return (result.rowcount or 0) > 0
