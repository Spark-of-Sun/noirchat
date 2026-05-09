"""
services/message_service.py
────────────────────────────
Business logic for storing and retrieving encrypted messages.

The server is a blind carrier — it stores ciphertext without
understanding it. Decryption happens exclusively in the receiver's
browser using keys derived from their passphrase.

Send flow:
1. Verify the session has a receiver attached (identity was verified)
2. Check receiver has sufficient balance
3. Deduct 1 credit atomically
4. Store ciphertext + sender's ephemeral public key
5. Sign HMAC ack token
6. Delete the session (one-use)
7. Return ack token to sender

Ack token delivery:
The ack token contains the receiver's ack_code, HMAC-signed.
The sender cannot forge this — they don't know the HMAC key.
The ack_code itself is NOT returned in plaintext here; it is part
of the signed token which the sender can verify is authentic.
"""
import logging
from datetime import datetime, timedelta, timezone
import asyncpg
import redis.asyncio as aioredis
from app.config import settings
from app.models.message import Message
from app.crypto.hmac_utils import sign_ack_token
from app.store.session_repo import load_session, delete_session
from app.store.message_repo import store_message, get_inbox, mark_read_and_soft_delete
from app.store.user_repo import get_user_by_id, deduct_balance

log = logging.getLogger(__name__)


class MessageError(Exception):
    """Base class for message service errors."""


class SessionNotReadyError(MessageError):
    """Identity was not verified before attempting to send."""


class InsufficientBalanceError(MessageError):
    """Receiver has no credits to accept this message."""


async def send_message(
    db: asyncpg.Pool,
    redis: aioredis.Redis,
    session_id: str,
    ciphertext: str,
    sender_ephemeral_pubkey: str,
) -> str:
    """
    Store an encrypted message and return a signed ack token.

    Args:
        db:                     Postgres pool
        redis:                  Redis client
        session_id:             Active verified session
        ciphertext:             Base64 ChaCha20-Poly1305 encrypted message
        sender_ephemeral_pubkey: Base64 X25519 sender public key

    Returns:
        HMAC-signed ack token string

    Raises:
        SessionNotReadyError if identity was not verified
        InsufficientBalanceError if receiver has 0 credits
    """
    # ── 1. Load and validate session ───────────────────────────────────
    session = await load_session(redis, session_id)
    if session is None or session.receiver_id is None:
        raise SessionNotReadyError("session_not_verified")

    receiver_id = session.receiver_id

    # ── 2. Load receiver and check balance ─────────────────────────────
    receiver = await get_user_by_id(db, receiver_id)
    if receiver is None:
        raise MessageError("receiver_not_found")

    if receiver.balance < 1:
        raise InsufficientBalanceError("insufficient_balance")

    # ── 3. Deduct credit atomically ────────────────────────────────────
    if not await deduct_balance(db, receiver_id):
        raise InsufficientBalanceError("insufficient_balance")

    # ── 4. Build and store message ─────────────────────────────────────
    expires_at = datetime.now(timezone.utc) + timedelta(days=receiver.msg_ttl_days)
    message_id = Message.new_id()
    ack_token = sign_ack_token(message_id, receiver.ack_code)

    message = Message(
        id=message_id,
        receiver_id=receiver_id,
        ciphertext=ciphertext,
        sender_ephemeral_pubkey=sender_ephemeral_pubkey,
        ack_token=ack_token,
        expires_at=expires_at,
    )
    await store_message(db, message)

    # ── 5. Expire the session (one-use, prevents re-send) ──────────────
    await delete_session(redis, session_id)

    log.info("message stored", extra={"message_id": message_id, "receiver_id": receiver_id})
    return ack_token


async def fetch_inbox(db: asyncpg.Pool, receiver_id: str) -> list[Message]:
    """
    Return the latest 10 unread messages for a receiver.
    The caller (receiver's browser) decrypts each ciphertext locally.
    """
    return await get_inbox(db, receiver_id)


async def read_and_delete(
    db: asyncpg.Pool,
    message_id: str,
    receiver_id: str,
) -> bool:
    """
    Soft-delete a message after the receiver has read and decrypted it.
    The hard delete runs via the TTL worker.
    """
    deleted = await mark_read_and_soft_delete(db, message_id, receiver_id)
    if deleted:
        log.info("message read+soft-deleted", extra={"message_id": message_id})
    return deleted