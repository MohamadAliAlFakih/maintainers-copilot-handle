"""SQL operations for the refresh_tokens table (rotating-refresh JWT auth)."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth.refresh_models import RefreshToken


def _hash_token(raw: str) -> str:
    """SHA-256 of the raw token. We never persist the raw token itself."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def issue_refresh_token(
    session: AsyncSession,
    user_id: uuid.UUID,
    lifetime_seconds: int,
) -> tuple[str, RefreshToken]:
    """Generates a fresh refresh token, stores its hash, returns (raw_token, row)."""
    raw = secrets.token_urlsafe(48)
    expires = datetime.now(UTC) + timedelta(seconds=lifetime_seconds)
    row = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=expires,
    )
    session.add(row)
    await session.flush()
    return raw, row


async def get_active_by_raw(session: AsyncSession, raw_token: str) -> RefreshToken | None:
    """Looks up an unrevoked, unexpired token by its raw value. Returns None otherwise."""
    if not raw_token:
        return None
    h = _hash_token(raw_token)
    result = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == h))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    now = datetime.now(UTC)
    if row.revoked_at is not None or row.expires_at <= now:
        return None
    return row


async def revoke(session: AsyncSession, token_id: uuid.UUID) -> None:
    """Marks a token revoked. Safe to call on already-revoked tokens (no-op)."""
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.id == token_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def rotate(
    session: AsyncSession,
    old_row: RefreshToken,
    lifetime_seconds: int,
) -> tuple[str, RefreshToken]:
    """Atomically revokes the old token and issues a fresh one chained to it."""
    raw_new, new_row = await issue_refresh_token(session, old_row.user_id, lifetime_seconds)
    old_row.revoked_at = datetime.now(UTC)
    old_row.replaced_by_id = new_row.id
    await session.flush()
    return raw_new, new_row
