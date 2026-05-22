"""Long-term semantic memory service — embeds facts and retrieves relevant ones per turn."""

import uuid
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.logging_setup import get_logger
from app.infra.modelserver_client import embed_texts
from app.infra.redaction import redact
from app.repositories.audit_log import write_audit_entry
from app.repositories.memory import insert_fact, search_facts

log = get_logger(__name__)


async def remember_fact(
    *,
    session: AsyncSession,
    http: httpx.AsyncClient,
    user_id: uuid.UUID,
    fact_text: str,
    source_message_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Embeds + persists a fact + writes audit log entry, all in one transaction.

    Returns a small status dict. The fact is REDACTED before persistence and audit.
    """
    redacted = redact(fact_text) or fact_text
    emb_list = await embed_texts(http, [redacted], which="bge")
    emb = emb_list[0]

    row = await insert_fact(
        session,
        user_id=user_id,
        fact_text=redacted,
        embedding=emb,
        source_message_id=source_message_id,
    )
    await write_audit_entry(
        session,
        actor_user_id=user_id,
        action="memory.write",
        target_type="long_term_memory",
        target_id=str(row.id),
        extra={"fact": redacted[:200]},
    )
    await session.commit()
    log.info("memory.remembered", user_id=str(user_id), fact_id=str(row.id))
    return {"saved": True, "fact_id": str(row.id), "fact": redacted}


async def recall_facts(
    *,
    session: AsyncSession,
    http: httpx.AsyncClient,
    user_id: uuid.UUID,
    current_message: str,
    top_k: int = 5,
) -> list[str]:
    """Returns the top-k most relevant fact texts for the current user message."""
    emb_list = await embed_texts(http, [current_message], which="bge")
    emb = emb_list[0]
    pairs = await search_facts(session, user_id=user_id, query_embedding=emb, top_k=top_k)
    return [fact for fact, _score in pairs]
