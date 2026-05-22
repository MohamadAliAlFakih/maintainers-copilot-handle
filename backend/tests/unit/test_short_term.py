"""Tests for the Redis-backed short-term memory."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.memory.short_term import (
    append_short_term,
    load_short_term,
    short_term_key,
)


def test_short_term_key_format():
    """The key includes the conversation id."""
    cid = "abc-123"
    assert short_term_key(cid) == "conversation:abc-123:messages"


@pytest.mark.asyncio
async def test_append_persists_and_refreshes_ttl():
    """append_short_term pushes a JSON message and refreshes the TTL to 24h."""
    redis = MagicMock()
    redis.rpush = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)

    await append_short_term(redis, "abc", {"role": "user", "content": "hi"})

    redis.rpush.assert_awaited_once()
    args = redis.rpush.await_args.args
    assert args[0] == "conversation:abc:messages"
    # value is a JSON string
    assert "hi" in args[1]
    redis.expire.assert_awaited_once_with(
        "conversation:abc:messages", 60 * 60 * 24
    )


@pytest.mark.asyncio
async def test_load_returns_parsed_messages():
    """load_short_term returns parsed dicts in order."""
    import json
    redis = MagicMock()
    redis.lrange = AsyncMock(
        return_value=[
            json.dumps({"role": "user", "content": "hi"}),
            json.dumps({"role": "assistant", "content": "hello"}),
        ]
    )
    redis.expire = AsyncMock(return_value=True)

    msgs = await load_short_term(redis, "abc", limit=10)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
