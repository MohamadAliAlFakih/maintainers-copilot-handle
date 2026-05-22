"""POST /chat/stream — SSE endpoint for the tool-calling chatbot."""
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from groq import AsyncGroq
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import (
    current_active_user,
    db_session_dep,
    groq_dep,
    modelserver_http_dep,
    rag_orchestrator_dep,
)
from app.domain.exceptions import NotFoundError
from app.repositories.conversations import create_conversation, get_conversation
from app.services.auth.models import User
from app.services.chat.loop import run_chat_loop
from app.services.rag.orchestrator import RagOrchestrator

router = APIRouter()


class ChatStreamRequest(BaseModel):
    """Inbound chat request."""

    message: str = Field(..., min_length=1, max_length=10_000)
    conversation_id: uuid.UUID | None = None


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    request: Request,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(db_session_dep),
    groq: AsyncGroq = Depends(groq_dep),
    http: httpx.AsyncClient = Depends(modelserver_http_dep),
    orchestrator: RagOrchestrator = Depends(rag_orchestrator_dep),
) -> StreamingResponse:
    """Streams the chatbot reply as SSE."""
    # Either resume an existing conversation or create a new one
    if payload.conversation_id is not None:
        existing = await get_conversation(session, payload.conversation_id)
        if existing is None or existing.user_id != user.id:
            raise NotFoundError("conversation not found")
        convo_id = payload.conversation_id
    else:
        convo = await create_conversation(session, user_id=user.id)
        await session.commit()
        convo_id = convo.id

    # The loop needs its own short-lived sessions, so build a factory bound to
    # the same engine the per-request session was opened on.
    factory: async_sessionmaker = async_sessionmaker(
        request.app.state.engine, expire_on_commit=False
    )

    async def event_gen():
        async for chunk in run_chat_loop(
            user_message=payload.message,
            conversation_id=convo_id,
            user_id=user.id,
            groq=groq,
            http=http,
            redis=request.app.state.redis,
            minio=request.app.state.minio,
            orchestrator=orchestrator,
            session_factory=factory,
            prompts_dir=Path("/app/prompts"),
        ):
            yield chunk

    return StreamingResponse(event_gen(), media_type="text/event-stream")
