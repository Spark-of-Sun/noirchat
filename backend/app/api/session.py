"""
api/session.py
──────────────
POST /v1/session/init

Creates an ephemeral session, generates an X25519 keypair and
challenge nonce. Returns the public key and nonce to the client.
The private key is encrypted and stored in Redis — never returned.
"""
from fastapi import APIRouter, Depends, status
import redis.asyncio as aioredis
from app.api.dependencies import get_redis
from app.api.schemas import SessionInitResponse
from app.services.session_service import create_session

router = APIRouter(prefix="/v1/session", tags=["session"])


@router.post(
    "/init",
    response_model=SessionInitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialise an ephemeral sender session",
)
async def session_init(
    redis: aioredis.Redis = Depends(get_redis),
) -> SessionInitResponse:
    """
    Start a new sender session.

    Returns:
    - `session_id`: opaque identifier for this session
    - `server_nonce`: 32-byte hex — used client-side to derive session_key
    - `server_pubkey`: X25519 public key for ECDH key exchange
    """
    session = await create_session(redis)
    return SessionInitResponse(
        session_id=session.session_id,
        server_nonce=session.server_nonce,
        server_pubkey=session.public_key_b64,
    )