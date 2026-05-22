"""SQL for messages."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat.models import Message


async def append_message(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    tool_calls: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
) -> Message:
    """Adds one message to a conversation."""
    m = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_results=tool_results,
    )
    session.add(m)
    await session.flush()
    return m


async def list_messages(
    session: AsyncSession, conversation_id: uuid.UUID, limit: int = 50
) -> list[Message]:
    """Returns the conversation's messages oldest-first up to `limit`."""
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())
