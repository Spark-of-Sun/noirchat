"""
models/user.py
──────────────
User domain model.

The passphrase is never stored. Only the Argon2id hash is stored.
All plaintext fields are set by the receiver — the server cannot
read incoming messages; only the receiver's browser can decrypt.
"""
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class User:
    id: str                          # UUID string
    username: str                    # Unique display name
    pass_hash: str                   # Argon2id hash of passphrase
    ack_code: str                    # 4–10 char confirmation code shown to senders
    balance: int                     # Credits for receiving messages
    msg_ttl_days: int = 7            # Auto-delete TTL for messages
    time_window_start: int | None = None  # UTC hour (0-23); None = always open
    time_window_end: int | None = None    # UTC hour (0-23)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())