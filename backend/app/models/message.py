"""
models/message.py
─────────────────
Message domain model.

The server stores ONLY ciphertext — it has no ability to read messages.
Decryption happens exclusively in the receiver's browser using
keys derived from their passphrase.
"""
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class Message:
    id: str                              # UUID string
    receiver_id: str                     # UUID of receiving user
    ciphertext: str                      # Base64 ChaCha20-Poly1305 ciphertext
    sender_ephemeral_pubkey: str         # Base64 X25519 sender public key
    ack_token: str                       # HMAC-signed delivery token
    expires_at: datetime                 # Hard TTL — background worker deletes after this
    is_read: bool = False
    read_at: datetime | None = None      # Soft delete timestamp
    created_at: datetime = field(default_factory=datetime.utcnow)

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())