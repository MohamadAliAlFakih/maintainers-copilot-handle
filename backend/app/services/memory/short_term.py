"""Redis-backed short-term conversation state with 24h sliding TTL."""
import json
from pathlib import Path
from typing import Any

from groq import AsyncGroq
from redis.asyncio import Redis

TTL_SECONDS = 60 * 60 * 24  # 24h, sliding (refreshed on every read/write)


def short_term_key(conversation_id: str) -> str:
    """Returns the Redis key for a conversation's message list."""
    return f"conversation:{conversation_id}:messages"


async def append_short_term(
    redis: Redis, conversation_id: str, message: dict[str, Any]
) -> None:
    """Pushes a JSON-serialized message and refreshes the TTL."""
    key = short_term_key(conversation_id)
    await redis.rpush(key, json.dumps(message))
    await redis.expire(key, TTL_SECONDS)


async def load_short_term(
    redis: Redis, conversation_id: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Returns the most recent `limit` messages and refreshes the TTL."""
    key = short_term_key(conversation_id)
    raw = await redis.lrange(key, -limit, -1)
    await redis.expire(key, TTL_SECONDS)
    return [json.loads(r) for r in raw]


async def count_short_term(redis: Redis, conversation_id: str) -> int:
    """Returns the total number of messages currently stored for this conversation."""
    return int(await redis.llen(short_term_key(conversation_id)))


async def trim_old(redis: Redis, conversation_id: str, keep_last: int) -> int:
    """Trims the list so only the last `keep_last` items remain. Returns count removed."""
    key = short_term_key(conversation_id)
    total = await count_short_term(redis, conversation_id)
    if total <= keep_last:
        return 0
    # ltrim keeps elements in [start, end] (inclusive); negative indices count from end
    await redis.ltrim(key, total - keep_last, -1)
    return total - keep_last


async def summarize_overflow(
    *,
    groq: AsyncGroq,
    model: str,
    prompts_dir: Path,
    messages: list[dict[str, Any]],
    _prompt_text: str | None = None,  # injectable for tests
) -> str:
    """Renders the conversation_summary prompt and returns the LLM's paragraph summary."""
    if _prompt_text is None:
        prompt = (prompts_dir / "conversation_summary.md").read_text(encoding="utf-8")
    else:
        prompt = _prompt_text

    rendered_msgs = "\n".join(
        f"{m['role'].upper()}: {m.get('content', '')}" for m in messages
    )
    rendered = prompt.replace("{{ messages }}", rendered_msgs)

    resp = await groq.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": rendered}],
        max_tokens=250,
        temperature=0.0,
    )
    return (resp.choices[0].message.content or "").strip()
