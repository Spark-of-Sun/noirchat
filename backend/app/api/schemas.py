"""
api/schemas.py
──────────────
All Pydantic request and response models.

Keeping schemas in one file makes the API contract easy to
audit at a glance. Each schema is small and focused.
"""
from pydantic import BaseModel, Field
from datetime import datetime


# ── Session ──────────────────────────────────────────────────────────

class SessionInitResponse(BaseModel):
    session_id: str
    server_nonce: str        # 32-byte hex — used by client to derive session_key
    server_pubkey: str       # Base64 X25519 public key


# ── Identity ─────────────────────────────────────────────────────────

class IdentityVerifyRequest(BaseModel):
    session_id: str
    username: str = Field(min_length=1, max_length=64)
    client_hmac_proof: str   # hex HMAC-SHA256(argon2_hash, server_nonce)


class IdentityVerifyResponse(BaseModel):
    verified: bool           # Always True on success; failure returns 401


# ── Message ──────────────────────────────────────────────────────────

class MessageSendRequest(BaseModel):
    session_id: str
    ciphertext: str           # Base64 ChaCha20-Poly1305 ciphertext
    sender_ephemeral_pubkey: str  # Base64 X25519 sender public key


class MessageSendResponse(BaseModel):
    message_id: str
    ack_token: str            # HMAC-signed ack token (contains ack_code)


class InboxMessageResponse(BaseModel):
    id: str
    ciphertext: str
    sender_ephemeral_pubkey: str
    created_at: datetime
    expires_at: datetime


class InboxResponse(BaseModel):
    messages: list[InboxMessageResponse]
    count: int


# ── Auth ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    passphrase: str = Field(min_length=1, max_length=512)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    passphrase: str = Field(min_length=8, max_length=512)
    ack_code: str = Field(min_length=4, max_length=10)


class RegisterResponse(BaseModel):
    user_id: str
    username: str


# ── Error ─────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str               # machine-readable code
    message: str             # human-readable detail