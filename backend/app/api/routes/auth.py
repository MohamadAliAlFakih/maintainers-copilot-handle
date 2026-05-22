"""Custom auth endpoints — rotating refresh-token issue/refresh/logout.

fastapi-users mounts /auth/jwt/login + /auth/register in main.py; this router
adds:
  POST /auth/login   — wraps fastapi-users login, also sets refresh cookie
  POST /auth/refresh — rotates the refresh cookie + issues a fresh access JWT
  POST /auth/logout  — revokes the current refresh token + clears cookie
"""

from fastapi import APIRouter, Depends, Form, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import db_session_dep
from app.config import get_settings
from app.domain.exceptions import AuthenticationFailed
from app.repositories.refresh_tokens import (
    get_active_by_raw,
    issue_refresh_token,
    revoke,
    rotate,
)
from app.services.auth.strategy import build_jwt_strategy

router = APIRouter()

REFRESH_COOKIE_NAME = "handle_refresh"


def _set_refresh_cookie(response: Response, raw: str, max_age: int, secure: bool) -> None:
    """Writes the refresh-token cookie with HttpOnly + SameSite=Lax."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/auth",
    )


def _clear_refresh_cookie(response: Response, secure: bool) -> None:
    """Removes the refresh cookie from the browser."""
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/auth", secure=secure)


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(db_session_dep),
) -> dict[str, str]:
    """Email + password login: returns access JWT and sets refresh cookie."""
    from fastapi_users.db import SQLAlchemyUserDatabase

    from app.services.auth.manager import UserManager
    from app.services.auth.models import User

    user_db = SQLAlchemyUserDatabase(session, User)
    manager = UserManager(user_db, session)
    creds_user = await manager.authenticate(
        type("C", (), {"username": username, "password": password})()  # OAuth2 form-like
    )
    if creds_user is None or not creds_user.is_active:
        raise AuthenticationFailed("invalid credentials")

    settings = get_settings()
    signing_key = request.app.state.vault_secrets.jwt_signing_key
    strategy = build_jwt_strategy(
        signing_key, lifetime_seconds=settings.jwt_lifetime_seconds
    )
    access_token = await strategy.write_token(creds_user)

    raw_refresh, _ = await issue_refresh_token(
        session, creds_user.id, lifetime_seconds=settings.refresh_lifetime_seconds
    )
    await session.commit()

    _set_refresh_cookie(
        response,
        raw_refresh,
        max_age=settings.refresh_lifetime_seconds,
        secure=settings.cookie_secure,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db_session_dep),
) -> dict[str, str]:
    """Rotates the refresh cookie and returns a fresh short-lived access token."""
    settings = get_settings()
    raw_old = request.cookies.get(REFRESH_COOKIE_NAME) or ""
    old_row = await get_active_by_raw(session, raw_old)
    if old_row is None:
        raise AuthenticationFailed("invalid or expired refresh token")

    raw_new, _new_row = await rotate(
        session, old_row, lifetime_seconds=settings.refresh_lifetime_seconds
    )
    await session.commit()

    # Fresh access token signed with the live JWT key
    signing_key = request.app.state.vault_secrets.jwt_signing_key
    strategy = build_jwt_strategy(
        signing_key, lifetime_seconds=settings.jwt_lifetime_seconds
    )

    from app.services.auth.models import User

    user = await session.get(User, old_row.user_id)
    if user is None:
        raise AuthenticationFailed("user no longer exists")
    access_token = await strategy.write_token(user)

    _set_refresh_cookie(
        response,
        raw_new,
        max_age=settings.refresh_lifetime_seconds,
        secure=settings.cookie_secure,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(db_session_dep),
) -> dict[str, str]:
    """Revokes the current refresh token and clears the cookie."""
    settings = get_settings()
    raw = request.cookies.get(REFRESH_COOKIE_NAME) or ""
    row = await get_active_by_raw(session, raw)
    if row is not None:
        await revoke(session, row.id)
        await session.commit()
    _clear_refresh_cookie(response, secure=settings.cookie_secure)
    return {"status": "logged_out"}
