"""Async SQLAlchemy engine + session factory."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(dsn: str) -> AsyncEngine:
    """Creates the app-wide async engine. Disposed on shutdown."""
    return create_async_engine(dsn, pool_pre_ping=True, echo=False)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Returns a session factory bound to the engine."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def yield_session(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Per-request session generator — closes the session even if the route raises."""
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
