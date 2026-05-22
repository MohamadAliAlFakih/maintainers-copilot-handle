"""Public widget config endpoint — used by the widget at load time."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import db_session_dep
from app.domain.exceptions import NotFoundError
from app.domain.schemas.widget import WidgetReadPublic
from app.repositories.widgets import get_widget_by_widget_id

router = APIRouter()


@router.get("/widgets/{widget_id}/config", response_model=WidgetReadPublic)
async def get_widget_config(
    widget_id: str,
    session: AsyncSession = Depends(db_session_dep),
) -> WidgetReadPublic:
    """Returns theme + greeting + enabled_tools. Origin protection happens at CORS layer."""
    w = await get_widget_by_widget_id(session, widget_id)
    if w is None:
        raise NotFoundError("widget not found")
    return WidgetReadPublic.model_validate(w)
