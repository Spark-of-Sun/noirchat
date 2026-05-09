"""
services/auth_service.py
─────────────────────────
Business logic for receiver dashboard login and JWT management.

The receiver authenticates with username + passphrase.
Argon2id verification runs here — the passphrase is used only
for login and is never stored or logged.
JWT tokens are short-lived (60 minutes default).
"""
import logging
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.config import settings
from app.crypto.hashing import verify_passphrase
from app.store.user_repo import get_user_by_username
import asyncpg

log = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised for any authentication failure — maps to 401."""


def _create_jwt(user_id: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> dict:
    """
    Decode and validate a JWT.
    Raises AuthError on invalid or expired tokens.
    """
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AuthError("invalid_token") from exc


async def login(db: asyncpg.Pool, username: str, passphrase: str) -> str:
    """
    Authenticate a receiver and return a signed JWT.

    Args:
        db:         Postgres pool
        username:   Receiver's username
        passphrase: Raw passphrase (used only for verification, never stored)

    Returns:
        JWT access token

    Raises:
        AuthError on invalid credentials
    """
    user = await get_user_by_username(db, username)

    # Always verify (even for fake hash) to prevent username enumeration via timing
    stored_hash = user.pass_hash if user else "$argon2id$v=19$m=65536,t=3,p=2$AAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    ok = verify_passphrase(stored_hash, passphrase)

    if not ok or user is None:
        log.warning("login failed", extra={"username": username})
        raise AuthError("invalid_credentials")

    token = _create_jwt(user.id, user.username)
    log.info("login success", extra={"user_id": user.id})
    return token