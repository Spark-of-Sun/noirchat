"""
api/auth.py
────────────
POST /v1/auth/register  — create a new receiver account
POST /v1/auth/login     — receiver login, returns JWT
GET  /v1/auth/me        — return current user profile (JWT protected)
"""
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg
from app.api.dependencies import get_db, get_current_user
from app.api.schemas import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
from app.services.auth_service import login, AuthError
from app.store.user_repo import create_user, get_user_by_username, get_user_by_id
from app.crypto.hashing import hash_passphrase
from app.models.user import User

router = APIRouter(prefix="/v1/auth", tags=["auth"])

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"error": "invalid_credentials", "message": "Invalid username or passphrase"},
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new receiver account",
)
async def register(
    body: RegisterRequest,
    db: asyncpg.Pool = Depends(get_db),
) -> RegisterResponse:
    """
    Create a receiver account.

    The passphrase is hashed with Argon2id here.
    The raw passphrase is never stored or logged.
    """
    # Check username availability
    existing = await get_user_by_username(db, body.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "username_taken", "message": "Username already exists"},
        )

    pass_hash = hash_passphrase(body.passphrase)
    user = User(
        id=User.new_id(),
        username=body.username,
        pass_hash=pass_hash,
        ack_code=body.ack_code,
        balance=10,  # Starting credits
    )
    await create_user(db, user)
    return RegisterResponse(user_id=user.id, username=user.username)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Receiver login — returns a JWT",
)
async def auth_login(
    body: LoginRequest,
    db: asyncpg.Pool = Depends(get_db),
) -> LoginResponse:
    """
    Authenticate a receiver with username + passphrase.
    Returns a short-lived JWT for dashboard access.
    """
    try:
        token = await login(db, body.username, body.passphrase)
    except AuthError:
        raise _UNAUTH

    return LoginResponse(access_token=token)


@router.get(
    "/me",
    summary="Return current authenticated user profile",
)
async def auth_me(
    db: asyncpg.Pool = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Return basic profile for the authenticated receiver."""
    profile = await get_user_by_id(db, user["sub"])
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": profile.id,
        "username": profile.username,
        "balance": profile.balance,
        "msg_ttl_days": profile.msg_ttl_days,
        "time_window_start": profile.time_window_start,
        "time_window_end": profile.time_window_end,
        "ack_code": profile.ack_code,
    }