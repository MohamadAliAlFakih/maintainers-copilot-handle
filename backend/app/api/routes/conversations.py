"""Conversation routes — list the user's chats, fetch messages, rename."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import current_active_user, db_session_dep
from app.domain.exceptions import NotFoundError
from app.repositories.conversations import (
    get_conversation,
    list_conversations_for_user,
    update_conversation_title,
)
from app.repositories.messages import list_messages
from app.services.auth.models import User

router = APIRouter()


class ConversationOut(BaseModel):
    """Compact conversation summary for the sidebar."""

    id: uuid.UUID
    title: str | None
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    """One persisted message."""

    role: str
    content: str
    created_at: str


class TitleUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


@router.get("/conversations/me", response_model=list[ConversationOut])
async def list_my_conversations(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(db_session_dep),
) -> list[ConversationOut]:
    """Returns the current user's conversations, most recent first."""
    rows = await list_conversations_for_user(session, user.id, limit=50)
    return [
        ConversationOut(
            id=r.id,
            title=r.title,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in rows
    ]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut],
)
async def get_my_conversation_messages(
    conversation_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(db_session_dep),
) -> list[MessageOut]:
    """Returns the persisted messages for a conversation owned by this user."""
    convo = await get_conversation(session, conversation_id)
    if convo is None or convo.user_id != user.id:
        raise NotFoundError("conversation not found")
    rows = await list_messages(session, conversation_id, limit=200)
    return [
        MessageOut(role=m.role, content=m.content, created_at=m.created_at.isoformat())
        for m in rows
        if m.role in ("user", "assistant")
    ]


@router.patch(
    "/conversations/{conversation_id}/title",
    response_model=ConversationOut,
)
async def rename_conversation(
    conversation_id: uuid.UUID,
    payload: TitleUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(db_session_dep),
) -> ConversationOut:
    """Renames a conversation owned by this user."""
    convo = await get_conversation(session, conversation_id)
    if convo is None or convo.user_id != user.id:
        raise NotFoundError("conversation not found")
    updated = await update_conversation_title(session, conversation_id, payload.title)
    assert updated is not None
    await session.commit()
    return ConversationOut(
        id=updated.id,
        title=updated.title,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )