"""
services/session_service.py
────────────────────────────
Business logic for ephemeral session lifecycle.

A session represents one sender's interaction window.
It holds the server-side ephemeral X25519 keypair and
the challenge nonce for replay protection.
Sessions expire in 5 minutes (SESSION_TTL_SECONDS).
"""
import uuid
import base64
import redis.asyncio as aioredis
from app.models.session import Session
from app.crypto.keypair import generate_x25519_keypair
from app.crypto.hashing import derive_nonce
from app.store.session_repo import save_session, load_session


async def create_session(redis: aioredis.Redis) -> Session:
    """
    Create a new ephemeral session:
    1. Generate X25519 keypair
    2. Generate challenge nonce
    3. Encrypt private key and store in Redis
    4. Return session (public key and nonce sent to client)
    """
    private_key_raw, public_key_raw = generate_x25519_keypair()
    nonce = derive_nonce()
    session_id = str(uuid.uuid4())

    session = Session(
        session_id=session_id,
        server_nonce=nonce,
        public_key_b64=base64.urlsafe_b64encode(public_key_raw).decode(),
        private_key_b64=base64.urlsafe_b64encode(private_key_raw).decode(),
    )
    await save_session(redis, session)
    return session


async def get_session(redis: aioredis.Redis, session_id: str) -> Session | None:
    """Load a session from Redis. Returns None if expired or not found."""
    return await load_session(redis, session_id)