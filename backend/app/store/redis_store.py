"""
store/redis_store.py
─────────────────────
Async Redis connection for session storage and rate limiting.

Redis holds only encrypted session blobs (see crypto/session_encrypt.py).
No plaintext keys, hashes, or secrets ever touch Redis.
"""
import redis.asyncio as aioredis
from app.config import settings

_client: aioredis.Redis | None = None


async def create_redis() -> aioredis.Redis:
    """Create the Redis client at startup."""
    global _client
    _client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    await _client.ping()
    return _client


async def close_redis() -> None:
    """Close the Redis connection at shutdown."""
    global _client
    if _client:
        await _client.aclose()
        _client = None


def get_redis() -> aioredis.Redis:
    """Return the live Redis client for dependency injection."""
    if _client is None:
        raise RuntimeError("Redis client not initialised")
    return _client