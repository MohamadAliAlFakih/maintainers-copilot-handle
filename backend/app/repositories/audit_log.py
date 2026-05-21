"""Audit log writer — append-only, redacts the `extra` payload before insert."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.redaction import redact
from app.services.auth.models import AuditLog


def _redact_extra(extra: dict[str, Any] | None) -> dict[str, Any] | None:
    """Walks an extra dict and redacts string values; non-string values pass through."""
    if extra is None:
        return None
    out: dict[str, Any] = {}
    for k, v in extra.items():
        out[k] = redact(v) if isinstance(v, str) else v
    return out


async def write_audit_entry(
    session: AsyncSession,
    *,
    actor_user_id: UUID | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> AuditLog:
    """Adds a new audit_log row; caller is responsible for committing the surrounding tx."""
    row = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        extra=_redact_extra(extra),
    )
    session.add(row)
    await session.flush()
    return row
