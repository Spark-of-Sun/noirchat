"""
api/dependencies.py
────────────────────
FastAPI dependency functions for injection into route handlers.

- get_db(): yields the Postgres pool
- get_redis(): yields the Redis client
- get_current_user(): extracts and validates JWT, returns user_id
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg
import redis.asyncio as aioredis
from app.store.database import get_pool
from app.store.redis_store import get_redis as _get_redis_client
from app.services.auth_service import decode_jwt, AuthError

_bearer = HTTPBearer()


def get_db() -> asyncpg.Pool:
    """Dependency: returns the live Postgres connection pool."""
    return get_pool()


def get_redis() -> aioredis.Redis:
    """Dependency: returns the live Redis client."""
    return _get_redis_client()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    Dependency: validates the Bearer JWT and returns the decoded payload.
    Use in protected routes:  user = Depends(get_current_user)
    Then: user["sub"] is the user_id, user["username"] is the username.
    """
    try:
        return decode_jwt(credentials.credentials)
    except AuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "Token is invalid or expired"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    