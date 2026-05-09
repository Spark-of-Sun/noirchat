"""
api/message.py
──────────────
POST /v1/message/send     — sender submits encrypted message
GET  /v1/message/inbox    — receiver fetches ciphertexts (JWT protected)
DELETE /v1/message/{id}   — receiver marks message read + soft deletes (JWT protected)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
import asyncpg
import redis.asyncio as aioredis
import logging
from app.api.dependencies import get_db, get_redis, get_current_user
from app.api.schemas import (
    MessageSendRequest, MessageSendResponse,
    InboxResponse, InboxMessageResponse,
)
from app.services.message_service import (
    send_message, fetch_inbox, read_and_delete,
    SessionNotReadyError, InsufficientBalanceError, MessageError,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/message", tags=["message"])


@router.post(
    "/send",
    response_model=MessageSendResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send an encrypted one-way message",
)
async def message_send(
    request: Request,
    body: MessageSendRequest,
    db: asyncpg.Pool = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> MessageSendResponse:
    """
    Submit an encrypted message payload.

    The session must already be verified via /identity/verify.
    The server stores only ciphertext — it cannot read the message.

    Returns:
    - `message_id`: UUID of the stored message
    - `ack_token`: HMAC-signed token proving delivery (contains receiver's ack_code)
    """
    try:
        ack_token = await send_message(
            db=db,
            redis=redis,
            session_id=body.session_id,
            ciphertext=body.ciphertext,
            sender_ephemeral_pubkey=body.sender_ephemeral_pubkey,
        )
    except SessionNotReadyError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "session_not_verified", "message": "Identity not verified for this session"},
        )
    except InsufficientBalanceError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"error": "insufficient_balance", "message": "Receiver cannot accept messages (no credits)"},
        )
    except MessageError as exc:
        log.error("message_send_error", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="server_error")

    # Extract message_id from ack_token payload (first segment before the dot)
    import base64
    payload_b64 = ack_token.split(".")[0]
    payload = base64.urlsafe_b64decode(payload_b64 + "==").decode()
    message_id = payload.split(":")[0]

    return MessageSendResponse(message_id=message_id, ack_token=ack_token)


@router.get(
    "/inbox",
    response_model=InboxResponse,
    summary="Fetch receiver inbox (latest 10 encrypted messages)",
)
async def message_inbox(
    db: asyncpg.Pool = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> InboxResponse:
    """
    Return the latest unread messages for the authenticated receiver.
    The ciphertext must be decrypted client-side — the server cannot read it.
    """
    messages = await fetch_inbox(db, user["sub"])
    return InboxResponse(
        messages=[
            InboxMessageResponse(
                id=m.id,
                ciphertext=m.ciphertext,
                sender_ephemeral_pubkey=m.sender_ephemeral_pubkey,
                created_at=m.created_at,
                expires_at=m.expires_at,
            )
            for m in messages
        ],
        count=len(messages),
    )


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark a message as read and schedule deletion",
)
async def message_delete(
    message_id: str,
    db: asyncpg.Pool = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> None:
    """
    Mark a message as read after the receiver has decrypted it.
    Soft-delete — the TTL worker performs the hard delete later.
    """
    deleted = await read_and_delete(db, message_id, user["sub"])
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Message not found or already read"},
        )