"""Memory inspector endpoints — user sees own; admin sees any."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import current_active_user, db_session_dep, require_admin
from app.domain.exceptions import NotFoundError
from app.repositories.audit_log import write_audit_entry
from app.repositories.memory import delete_fact, list_facts_for_user
from app.services.auth.models import User

router = APIRouter()


class FactRead(BaseModel):
    """Outbound shape for one fact."""

    id: uuid.UUID
    fact_text: str
    created_at: str


@router.get("/me", response_model=list[FactRead])
async def list_my_memory(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(db_session_dep),
) -> list[FactRead]:
    """Returns the authenticated user's facts."""
    facts = await list_facts_for_user(session, user.id)
    return [
        FactRead(id=f.id, fact_text=f.fact_text, created_at=f.created_at.isoformat()) for f in facts
    ]


@router.delete("/me/{fact_id}", status_code=204)
async def delete_my_memory(
    fact_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(db_session_dep),
) -> None:
    """Deletes one of the user's own facts."""
    ok = await delete_fact(session, fact_id, user.id)
    if not ok:
        raise NotFoundError("fact not found")
    await write_audit_entry(
        session,
        actor_user_id=user.id,
        action="memory.delete",
        target_type="long_term_memory",
        target_id=str(fact_id),
    )
    await session.commit()


@router.get("/admin/{user_id}", response_model=list[FactRead])
async def list_any_user_memory(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(db_session_dep),
) -> list[FactRead]:
    """Admin-only view of any user's memory."""
    facts = await list_facts_for_user(session, user_id)
    return [
        FactRead(id=f.id, fact_text=f.fact_text, created_at=f.created_at.isoformat()) for f in facts
    ]
