"""Admin-only widget CRUD."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import db_session_dep, require_admin
from app.domain.exceptions import NotFoundError
from app.domain.schemas.widget import (
    WidgetCreate,
    WidgetReadAdmin,
    WidgetUpdate,
)
from app.repositories.audit_log import write_audit_entry
from app.repositories.widgets import (
    create_widget,
    get_widget_by_widget_id,
    list_widgets,
    update_widget,
)
from app.services.auth.models import User
from app.services.widgets import invalidate_origins_cache

router = APIRouter()


@router.get("/", response_model=list[WidgetReadAdmin])
async def list_all(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(db_session_dep),
) -> list[WidgetReadAdmin]:
    """Lists every widget (admin only)."""
    return [WidgetReadAdmin.model_validate(w) for w in await list_widgets(session)]


@router.post("/", response_model=WidgetReadAdmin, status_code=status.HTTP_201_CREATED)
async def create(
    payload: WidgetCreate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(db_session_dep),
) -> WidgetReadAdmin:
    """Creates a new widget config."""
    w = await create_widget(
        session,
        name=payload.name,
        allowed_origins=payload.allowed_origins,
        theme=payload.theme,
        greeting=payload.greeting,
        enabled_tools=payload.enabled_tools,
        created_by_user_id=admin.id,
    )
    await write_audit_entry(
        session,
        actor_user_id=admin.id,
        action="widget.create",
        target_type="widget",
        target_id=w.widget_id,
    )
    await session.commit()
    invalidate_origins_cache(w.widget_id)
    return WidgetReadAdmin.model_validate(w)


@router.patch("/{widget_id}", response_model=WidgetReadAdmin)
async def update(
    widget_id: str,
    payload: WidgetUpdate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(db_session_dep),
) -> WidgetReadAdmin:
    """Partial-updates a widget config."""
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    w = await update_widget(session, widget_id, updates)
    if w is None:
        raise NotFoundError("widget not found")
    await write_audit_entry(
        session,
        actor_user_id=admin.id,
        action="widget.config.update",
        target_type="widget",
        target_id=widget_id,
        extra={"fields": list(updates.keys())},
    )
    await session.commit()
    invalidate_origins_cache(widget_id)
    return WidgetReadAdmin.model_validate(w)


@router.get("/{widget_id}", response_model=WidgetReadAdmin)
async def get_one(
    widget_id: str,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(db_session_dep),
) -> WidgetReadAdmin:
    """Fetches one widget by widget_id."""
    w = await get_widget_by_widget_id(session, widget_id)
    if w is None:
        raise NotFoundError("widget not found")
    return WidgetReadAdmin.model_validate(w)
