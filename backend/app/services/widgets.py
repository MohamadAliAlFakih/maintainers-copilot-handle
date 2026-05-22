"""Widget ORM model + helpers for slug generation."""
import asyncio
import secrets
import uuid
from datetime import datetime
from time import time

from sqlalchemy import ARRAY, JSON, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.services.auth.models import Base


def generate_widget_id() -> str:
    """Generates a public opaque widget id like 'wgt_a8d31c4f'."""
    return f"wgt_{secrets.token_hex(4)}"


class Widget(Base):
    """An embeddable widget config keyed by a public opaque id."""

    __tablename__ = "widgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    widget_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=generate_widget_id
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    allowed_origins: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    theme: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    greeting: Mapped[str] = mapped_column(Text, nullable=False, default="How can I help?")
    enabled_tools: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ----- Allowed-origins cache (5-min TTL) -----

_CACHE: dict[str, tuple[float, frozenset[str]]] = {}
_CACHE_TTL = 300.0
_CACHE_LOCK = asyncio.Lock()


async def get_allowed_origins(session, widget_id: str) -> frozenset[str] | None:  # type: ignore[no-untyped-def]
    """Returns the cached allowed-origins set, or fetches from DB. None if widget not found."""
    now = time()
    cached = _CACHE.get(widget_id)
    if cached and cached[0] > now:
        return cached[1]

    async with _CACHE_LOCK:
        cached = _CACHE.get(widget_id)
        if cached and cached[0] > now:
            return cached[1]

        from app.repositories.widgets import get_widget_by_widget_id

        widget = await get_widget_by_widget_id(session, widget_id)
        if widget is None:
            return None
        origins = frozenset(widget.allowed_origins)
        _CACHE[widget_id] = (now + _CACHE_TTL, origins)
        return origins


def invalidate_origins_cache(widget_id: str | None = None) -> None:
    """Drops one widget's cached origins, or the entire cache if widget_id is None."""
    if widget_id is None:
        _CACHE.clear()
    else:
        _CACHE.pop(widget_id, None)
