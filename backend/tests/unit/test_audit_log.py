"""Tests for the audit log writer — verifies redaction is applied to the `extra` dict."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.repositories.audit_log import write_audit_entry


@pytest.mark.asyncio
async def test_write_audit_entry_inserts_redacted_extra():
    """The extra payload must be redacted before being passed to session.add."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    user_id = uuid4()
    leaky_extra = {"note": "user pasted token sk-abcdefghijklmnopqrstuvwxyz0123456789"}

    await write_audit_entry(
        session,
        actor_user_id=user_id,
        action="memory.write",
        target_type="memory",
        target_id="mem-1",
        extra=leaky_extra,
    )

    session.add.assert_called_once()
    added_obj = session.add.call_args.args[0]
    assert added_obj.action == "memory.write"
    assert added_obj.actor_user_id == user_id
    assert "sk-abcdefghijklmnop" not in str(added_obj.extra)
    assert "[REDACTED:api_key]" in str(added_obj.extra)
