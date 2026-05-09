"""
api/identity.py
────────────────
POST /v1/identity/verify

Verifies sender knowledge of receiver passphrase using challenge-response.
Returns ONLY { "verified": true } — no receiver metadata is ever returned here.
All failure paths return 401 with an identical body to prevent information leakage.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
import asyncpg
import redis.asyncio as aioredis
import logging
from app.api.dependencies import get_db, get_redis
from app.api.schemas import IdentityVerifyRequest, IdentityVerifyResponse
from app.services.identity_service import verify_identity, IdentityVerificationError

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/identity", tags=["identity"])

# Uniform 401 response — identical for every failure path
_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"error": "verification_failed", "message": "Verification failed"},
)


@router.post(
    "/verify",
    response_model=IdentityVerifyResponse,
    summary="Verify sender identity via challenge-response",
)
async def identity_verify(
    request: Request,
    body: IdentityVerifyRequest,
    db: asyncpg.Pool = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> IdentityVerifyResponse:
    """
    Verify that the sender knows the receiver's passphrase
    without transmitting the passphrase or its hash.

    The client must send:
    - `session_id`: from /session/init
    - `username`: receiver's username
    - `client_hmac_proof`: HMAC-SHA256(argon2id_hash, server_nonce) in hex

    Returns `{ "verified": true }` on success, 401 on any failure.
    """
    try:
        await verify_identity(
            db=db,
            redis=redis,
            session_id=body.session_id,
            username=body.username,
            client_hmac_proof=body.client_hmac_proof,
        )
    except IdentityVerificationError as exc:
        # Log with request ID for audit trail — never expose reason in response
        log.warning(
            "identity_verify_failed",
            extra={
                "reason": str(exc),
                "request_id": getattr(request.state, "request_id", "-"),
            },
        )
        raise _UNAUTH

    return IdentityVerifyResponse(verified=True)