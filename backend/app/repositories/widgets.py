"""SQL for the widgets table."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.widgets import Widget


async def create_widget(
    session: AsyncSession,
    *,
    name: str,
    allowed_origins: list[str],
    theme: dict,
    greeting: str,
    enabled_tools: list[str],
    created_by_user_id: uuid.UUID,
) -> Widget:
    """Inserts a new widget config."""
    w = Widget(
        name=name,
        allowed_origins=allowed_origins,
        theme=theme,
        greeting=greeting,
        enabled_tools=enabled_tools,
        created_by_user_id=created_by_user_id,
    )
    session.add(w)
    await session.flush()
    return w


async def get_widget_by_widget_id(
    session: AsyncSession, widget_id: str
) -> Widget | None:
    """Looks up a widget by its public opaque widget_id."""
    result = await session.execute(select(Widget).where(Widget.widget_id == widget_id))
    return result.scalar_one_or_none()


async def list_widgets(session: AsyncSession) -> list[Widget]:
    """Returns all widgets (admin-only call)."""
    result = await session.execute(select(Widget).order_by(Widget.created_at.desc()))
    return list(result.scalars().all())


async def update_widget(
    session: AsyncSession, widget_id: str, updates: dict
) -> Widget | None:
    """Updates a widget by widget_id. Returns the updated row or None if not found."""
    w = await get_widget_by_widget_id(session, widget_id)
    if w is None:
        return None
    for k, v in updates.items():
        if hasattr(w, k):
            setattr(w, k, v)
    await session.flush()
    return w
