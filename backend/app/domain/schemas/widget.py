"""DTOs for widget endpoints — separate public vs admin shapes."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WidgetCreate(BaseModel):
    """Admin-only payload for creating a widget."""

    name: str = Field(..., min_length=1, max_length=200)
    allowed_origins: list[str] = Field(default_factory=list, max_length=20)
    theme: dict = Field(default_factory=dict)
    greeting: str = Field("How can I help?", max_length=500)
    enabled_tools: list[str] = Field(default_factory=list)


class WidgetUpdate(BaseModel):
    """Admin-only payload for partial update."""

    name: str | None = None
    allowed_origins: list[str] | None = None
    theme: dict | None = None
    greeting: str | None = None
    enabled_tools: list[str] | None = None


class WidgetReadAdmin(BaseModel):
    """Admin view — includes all fields."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    widget_id: str
    name: str
    allowed_origins: list[str]
    theme: dict
    greeting: str
    enabled_tools: list[str]
    created_at: datetime
    updated_at: datetime


class WidgetReadPublic(BaseModel):
    """Public view (used by the widget at load time) — hides allowed_origins."""

    model_config = ConfigDict(from_attributes=True)

    widget_id: str
    theme: dict
    greeting: str
    enabled_tools: list[str]
