"""UserManager — hooks fastapi-users into our DB and emits audit entries."""

import uuid
from typing import Any

from fastapi import Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.logging_setup import get_logger
from app.repositories.audit_log import write_audit_entry
from app.services.auth.models import User

log = get_logger(__name__)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Manages user lifecycle events; logs registration and login to audit_log."""

    # Required by fastapi-users API; unused because we don't expose reset/verify routes.
    reset_password_token_secret = "unused-not-implemented-yet"
    verification_token_secret = "unused-not-implemented-yet"

    def __init__(self, user_db: Any, session: AsyncSession) -> None:
        super().__init__(user_db)
        self._session = session

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        """Records new user registration."""
        log.info("auth.registered", user_id=str(user.id), email=user.email)
        await write_audit_entry(
            self._session,
            actor_user_id=user.id,
            action="user.register",
            target_type="user",
            target_id=str(user.id),
        )
        await self._session.commit()

    async def on_after_login(
        self,
        user: User,
        request: Request | None = None,
        response: Any = None,
    ) -> None:
        """Records each successful login."""
        log.info("auth.login", user_id=str(user.id))
        await write_audit_entry(
            self._session,
            actor_user_id=user.id,
            action="user.login",
            target_type="user",
            target_id=str(user.id),
        )
        await self._session.commit()
