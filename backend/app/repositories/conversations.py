"""SQL for conversations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat.models import Conversation


async def create_conversation(
    session: AsyncSession, user_id: uuid.UUID, title: str | None = None
) -> Conversation:
    """Inserts a new conversation row for the user."""
    c = Conversation(user_id=user_id, title=title)
    session.add(c)
    await session.flush()
    return c


async def get_conversation(
    session: AsyncSession, conversation_id: uuid.UUID
) -> Conversation | None:
    """Fetches a conversation by id; None if missing."""
    result = await session.execute(select(Conversation).where(Conversation.id == conversation_id))
    return result.scalar_one_or_none()


async def list_conversations_for_user(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 50
) -> list[Conversation]:
    """Returns the user's most recent conversations."""
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
