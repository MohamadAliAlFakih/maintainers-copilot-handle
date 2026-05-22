"""Alembic env for async SQLAlchemy — builds DSN from app Settings."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.config import get_settings
from app.services.auth.models import Base
from app.services.chat.models import Conversation, Message  # noqa: F401  -- registers chat tables on Base.metadata
from app.services.memory.models import LongTermMemory  # noqa: F401  -- registers long-term memory table on Base.metadata
from app.services.rag.models import Chunk  # noqa: F401  -- registers chunks table on Base.metadata

config = context.config

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Runs migrations without a DB connection (sql-only output)."""
    url = get_settings().db_dsn
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    """Runs migrations in 'online' mode within a sync wrapper."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Builds an async engine and runs migrations against it."""
    settings = get_settings()
    connectable = create_async_engine(settings.db_dsn, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
