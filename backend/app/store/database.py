"""
store/database.py
─────────────────
Async PostgreSQL connection pool using asyncpg.

The pool is created at application startup and closed at shutdown.
All repositories receive the pool via dependency injection —
they never create connections themselves.
"""
import asyncpg
from app.config import settings

# Module-level pool reference; initialised in lifespan()
_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    """
    Create and return the global connection pool.
    Called once at application startup.
    """
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    return _pool


async def close_pool() -> None:
    """Close the pool gracefully on application shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """
    Return the live pool for FastAPI dependency injection.
    Raises RuntimeError if called before create_pool().
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialised")
    return _pool