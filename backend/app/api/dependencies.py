"""Shared FastAPI dependencies — exposes app.state resources via Depends()."""

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from fastapi import Depends, Request
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from groq import AsyncGroq
from minio import Minio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.domain.enums import Role
from app.domain.exceptions import PermissionDenied
from app.infra.db import yield_session
from app.services.auth.manager import UserManager
from app.services.auth.models import User
from app.services.rag.orchestrator import RagOrchestrator


def settings_dep() -> Settings:
    """Returns the cached Settings singleton."""
    return get_settings()


def minio_dep(request: Request) -> Minio:
    """Returns the lifespan-created MinIO client."""
    return request.app.state.minio


def redis_dep(request: Request) -> Redis:
    """Returns the lifespan-created Redis client."""
    return request.app.state.redis


async def db_session_dep(request: Request) -> AsyncIterator[AsyncSession]:
    """Per-request DB session, closed on response (even on exceptions)."""
    factory = request.app.state.session_factory
    async for session in yield_session(factory):
        yield session


# ----- fastapi-users wiring -----

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def _jwt_strategy_factory(request: Request) -> JWTStrategy:
    """Returns the JWT strategy built once at lifespan startup."""
    return request.app.state.jwt_strategy


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=_jwt_strategy_factory,  # type: ignore[arg-type]
)


async def get_user_db(
    session: AsyncSession = Depends(db_session_dep),
) -> AsyncIterator[SQLAlchemyUserDatabase[User, uuid.UUID]]:
    """Yields a SQLAlchemy user database bound to the request session."""
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(
    session: AsyncSession = Depends(db_session_dep),
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncIterator[UserManager]:
    """Yields a UserManager bound to the request session for audit-log writes."""
    yield UserManager(user_db, session)


fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
"""Dependency: returns the authenticated User. 401 if no/invalid token."""


async def require_admin(user: User = Depends(current_active_user)) -> User:
    """Dependency: returns the user iff role is admin; raises PermissionDenied (403) otherwise."""
    if user.role != Role.ADMIN.value:
        raise PermissionDenied("admin role required")
    return user


# ----- RAG wiring (Plan 2b) -----


def groq_dep(request: Request) -> AsyncGroq:
    """Returns the lifespan-created Groq client."""
    return request.app.state.groq


def modelserver_http_dep(request: Request) -> httpx.AsyncClient:
    """Returns the lifespan-created modelserver httpx client."""
    return request.app.state.modelserver_http


def rag_orchestrator_dep(
    settings: Settings = Depends(settings_dep),
    groq: AsyncGroq = Depends(groq_dep),
    http: httpx.AsyncClient = Depends(modelserver_http_dep),
) -> RagOrchestrator:
    """Builds a RagOrchestrator scoped to this request."""
    return RagOrchestrator(
        groq=groq,
        groq_model_cheap="llama-3.1-8b-instant",
        prompts_dir=Path("/app/prompts"),
        modelserver_http=http,
    )
