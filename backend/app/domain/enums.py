"""Domain enums — plain string-valued for DB-friendliness and JSON serialization."""
from enum import StrEnum


class Role(StrEnum):
    """User access role; gated by require_admin dependency for elevated routes."""

    USER = "user"
    ADMIN = "admin"
