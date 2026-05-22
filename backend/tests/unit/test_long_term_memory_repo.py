"""Tests for the long-term memory repository."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.repositories.memory import insert_fact


@pytest.mark.asyncio
async def test_insert_fact_calls_session_add():
    """insert_fact constructs a LongTermMemory row and adds it to the session."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    user_id = uuid4()

    row = await insert_fact(
        session, user_id=user_id, fact_text="prefers concise answers", embedding=[0.1] * 384
    )

    session.add.assert_called_once()
    assert row.user_id == user_id
    assert row.fact_text == "prefers concise answers"
    assert len(row.embedding) == 384
