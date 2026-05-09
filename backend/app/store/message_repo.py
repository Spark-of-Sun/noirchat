"""
store/message_repo.py
──────────────────────
All database operations for the messages table.

The server stores only ciphertext — it cannot read message content.
Soft deletes (read_at) are used; hard deletes run via the TTL worker.
"""
import asyncpg
from datetime import datetime
from app.models.message import Message


async def store_message(pool: asyncpg.Pool, message: Message) -> Message:
    """Insert an encrypted message. The server stores only opaque ciphertext."""
    await pool.execute(
        """
        INSERT INTO messages (id, receiver_id, ciphertext, sender_ephemeral_pubkey,
                              ack_token, expires_at, is_read, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        """,
        message.id, message.receiver_id, message.ciphertext,
        message.sender_ephemeral_pubkey, message.ack_token,
        message.expires_at, message.is_read, message.created_at,
    )
    return message


async def get_inbox(
    pool: asyncpg.Pool,
    receiver_id: str,
    limit: int = 10,
) -> list[Message]:
    """
    Fetch the latest unread messages for a receiver.
    Returns at most `limit` rows, newest first.
    Expired messages are excluded.
    """
    rows = await pool.fetch(
        """
        SELECT * FROM messages
        WHERE receiver_id = $1
          AND is_read = FALSE
          AND expires_at > now()
        ORDER BY created_at DESC
        LIMIT $2
        """,
        receiver_id, limit,
    )
    return [_row_to_message(r) for r in rows]


async def mark_read_and_soft_delete(
    pool: asyncpg.Pool,
    message_id: str,
    receiver_id: str,
) -> bool:
    """
    Atomically mark a message as read.
    The hard delete runs later via the TTL worker — this prevents
    the read/delete race condition where two concurrent requests
    both fetch before deletion fires.

    Returns True if a row was updated, False if not found (or wrong receiver).
    """
    result = await pool.fetchrow(
        """
        UPDATE messages
        SET is_read = TRUE, read_at = now()
        WHERE id = $1 AND receiver_id = $2 AND is_read = FALSE
        RETURNING id
        """,
        message_id, receiver_id,
    )
    return result is not None


async def hard_delete_expired(pool: asyncpg.Pool) -> int:
    """
    Permanently delete messages that are either:
      - Past their expires_at TTL (regardless of read status)
      - Already marked as read (immediate cleanup eligible)

    Called by the TTL worker on a schedule.
    Returns the number of rows deleted.
    """
    result = await pool.execute(
        """
        DELETE FROM messages
        WHERE expires_at < now()
           OR is_read = TRUE
        """
    )
    # asyncpg returns "DELETE N" string — extract the count
    return int(result.split()[-1])


def _row_to_message(row: asyncpg.Record) -> Message:
    return Message(
        id=str(row["id"]),
        receiver_id=str(row["receiver_id"]),
        ciphertext=row["ciphertext"],
        sender_ephemeral_pubkey=row["sender_ephemeral_pubkey"],
        ack_token=row["ack_token"],
        expires_at=row["expires_at"],
        is_read=row["is_read"],
        read_at=row["read_at"],
        created_at=row["created_at"],
    )