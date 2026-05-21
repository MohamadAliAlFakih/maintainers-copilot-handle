"""Async Redis client adapter for short-term memory + cache."""
import redis.asyncio as redis


def build_redis_client(host: str, port: int) -> redis.Redis:
    """Builds an async Redis client. Single instance per process."""
    return redis.Redis(
        host=host,
        port=port,
        decode_responses=True,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
    )
