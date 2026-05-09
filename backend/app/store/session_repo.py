"""
store/session_repo.py
──────────────────────
Ephemeral session storage backed by Redis.

Session data is AES-256-GCM encrypted before write.
Redis stores opaque encrypted blobs — never raw keys.
Keys expire automatically via Redis TTL.
"""
import json
import redis.asyncio as aioredis
from app.config import settings
from app.models.session import Session
from app.crypto.session_encrypt import encrypt_session_data, decrypt_session_data


_KEY_PREFIX = "session:"


def _redis_key(session_id: str) -> str:
    return f"{_KEY_PREFIX}{session_id}"


async def save_session(redis: aioredis.Redis, session: Session) -> None:
    """
    Serialize, encrypt, and store a session in Redis with TTL.

    The private key is stored inside the encrypted blob — it never
    appears as a plain value in Redis.
    """
    payload = json.dumps({
        "session_id": session.session_id,
        "server_nonce": session.server_nonce,
        "public_key_b64": session.public_key_b64,
        "private_key_b64": session.private_key_b64,
        "receiver_id": session.receiver_id,
    })
    encrypted_blob = encrypt_session_data(payload)
    await redis.setex(
        _redis_key(session.session_id),
        settings.session_ttl_seconds,
        encrypted_blob,
    )


async def load_session(redis: aioredis.Redis, session_id: str) -> Session | None:
    """
    Load and decrypt a session from Redis.
    Returns None if the session has expired or doesn't exist.
    """
    blob = await redis.get(_redis_key(session_id))
    if blob is None:
        return None

    try:
        data = json.loads(decrypt_session_data(blob))
    except ValueError:
        # Decryption failed — treat as missing (log this externally)
        return None

    return Session(**data)


async def update_session_receiver(
    redis: aioredis.Redis,
    session: Session,
    receiver_id: str,
) -> None:
    """
    After identity verification succeeds, attach the receiver_id to the session.
    Refreshes the TTL to prevent expiry during message composition.
    """
    session.receiver_id = receiver_id
    await save_session(redis, session)


async def delete_session(redis: aioredis.Redis, session_id: str) -> None:
    """Explicitly remove a session — called after message delivery."""
    await redis.delete(_redis_key(session_id))