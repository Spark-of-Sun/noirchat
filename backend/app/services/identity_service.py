"""
services/identity_service.py
──────────────────────────────
Business logic for sender identity verification.

Security model:
- The sender enters the receiver's passphrase (shared out-of-band).
- The browser hashes it with Argon2id locally.
- The browser derives: session_key = HMAC-SHA256(argon2_hash, server_nonce)
- The server looks up the receiver's stored Argon2id hash and re-derives session_key.
- Verification succeeds if the proofs match using constant-time comparison.
- The server NEVER learns the raw passphrase.
- The nonce is single-use — replay attacks return a different session_key and fail.

Time window enforcement:
- If the receiver configured a time window, messages are rejected outside it.
- This is a UTC-based check on the server — not controlled by the client.

Error policy:
- All failure paths raise the same IdentityVerificationError.
- The handler maps this to a uniform 401 response with no detail.
- Response timing is equalised by the jitter middleware.
"""
import hmac
import hashlib
import base64
import logging
from datetime import datetime, timezone
import asyncpg
import redis.asyncio as aioredis
from app.store.user_repo import get_user_by_username
from app.store.session_repo import load_session, update_session_receiver

log = logging.getLogger(__name__)


class IdentityVerificationError(Exception):
    """Raised for any verification failure — maps to 401 with no detail."""


async def verify_identity(
    db: asyncpg.Pool,
    redis: aioredis.Redis,
    session_id: str,
    username: str,
    client_hmac_proof: str,   # hex-encoded HMAC(argon2_hash, server_nonce) from client
) -> str:
    """
    Verify the sender's knowledge of the receiver's passphrase
    using challenge-response — no hash is transmitted.

    Args:
        db:                Postgres pool
        redis:             Redis client
        session_id:        Active session UUID
        username:          Receiver's username
        client_hmac_proof: hex HMAC-SHA256(client_argon2_hash, session.server_nonce)

    Returns:
        receiver_id (UUID string) on success

    Raises:
        IdentityVerificationError on any failure
    """
    # ── 1. Load the session ────────────────────────────────────────────
    session = await load_session(redis, session_id)
    if session is None:
        log.warning("identity_verify: session not found or expired", extra={"session_id": session_id})
        raise IdentityVerificationError("session_expired")

    # ── 2. Fetch receiver's stored hash ────────────────────────────────
    user = await get_user_by_username(db, username)
    if user is None:
        log.warning("identity_verify: username not found", extra={"username": username})
        # Delay is handled by jitter middleware — don't add artificial sleep here
        raise IdentityVerificationError("receiver_not_found")

    # ── 3. Enforce time window (if configured) ──────────────────────────
    _check_time_window(user.time_window_start, user.time_window_end)

    # ── 4. Re-derive expected session_key from stored hash + nonce ────
    # session_key = HMAC-SHA256(stored_pass_hash_bytes, server_nonce_bytes)
    stored_hash_bytes = user.pass_hash.encode()
    nonce_bytes = bytes.fromhex(session.server_nonce)
    expected_proof = hmac.new(stored_hash_bytes, nonce_bytes, hashlib.sha256).hexdigest()

    # ── 5. Constant-time comparison ────────────────────────────────────
    if not hmac.compare_digest(expected_proof, client_hmac_proof.lower()):
        log.warning("identity_verify: HMAC proof mismatch", extra={"username": username})
        raise IdentityVerificationError("hmac_mismatch")

    # ── 6. Attach receiver to session ──────────────────────────────────
    await update_session_receiver(redis, session, user.id)
    log.info("identity_verify: success", extra={"receiver_id": user.id})
    return user.id


def _check_time_window(start_hour: int | None, end_hour: int | None) -> None:
    """
    Enforce the receiver's configured acceptance time window.
    Raises IdentityVerificationError if outside the window.
    """
    if start_hour is None or end_hour is None:
        return  # No window configured — always open

    current_hour = datetime.now(timezone.utc).hour

    if start_hour <= end_hour:
        # e.g. 09:00–17:00
        in_window = start_hour <= current_hour < end_hour
    else:
        # Wraps midnight e.g. 22:00–06:00
        in_window = current_hour >= start_hour or current_hour < end_hour

    if not in_window:
        raise IdentityVerificationError("outside_time_window")