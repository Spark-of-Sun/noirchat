"""
models/session.py
─────────────────
Ephemeral sender session.

Lives only in Redis with a short TTL (5 minutes max).
The private key field is AES-GCM encrypted before storage —
Redis holds an opaque blob, not a raw key.
"""
from dataclasses import dataclass


@dataclass
class Session:
    session_id: str           # UUID, used as Redis key suffix
    server_nonce: str         # 32-byte hex nonce for challenge-response
    public_key_b64: str       # X25519 server public key (sent to client)
    private_key_b64: str      # X25519 server private key (AES-GCM encrypted in Redis)
    receiver_id: str | None = None  # Set after identity verification succeeds