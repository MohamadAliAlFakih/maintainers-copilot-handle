"""Widget ORM model + helpers for slug generation."""
import secrets
import uuid
from datetime import datetime

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
