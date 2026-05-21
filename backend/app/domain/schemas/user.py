"""User DTOs — separate from the ORM model so password hashes never leak in responses."""

import uuid
from datetime import datetime

from fastapi_users import schemas
from pydantic import ConfigDict

from app.domain.enums import Role


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Outbound user shape returned to clients — hashed_password NOT included."""

    model_config = ConfigDict(from_attributes=True)

    role: Role
    created_at: datetime


class UserCreate(schemas.BaseUserCreate):
    """Inbound registration payload — email + password only; role is forced to 'user'."""


class UserUpdate(schemas.BaseUserUpdate):
    """Inbound update payload — clients cannot change their own role."""
