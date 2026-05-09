"""
crypto/hashing.py
─────────────────
Argon2id passphrase hashing for receiver identity storage.

Why Argon2id:
  - Memory-hard: makes GPU/ASIC brute-force expensive
  - Time-hard: configurable iteration cost
  - Side-channel resistant: id variant combines i and d
  - Winner of the Password Hashing Competition (2015)

The server verifies Argon2id hashes from the database.
The actual hashing of the passphrase happens client-side (browser)
using argon2-browser WASM. The server only stores and verifies hashes.
"""
import os
import hmac
import hashlib
import base64
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

# Argon2id parameters — these can be increased for higher security at the cost of speed.
# These values are conservative; increase memory_cost and time_cost for production.
_hasher = PasswordHasher(
    time_cost=3,         # number of iterations
    memory_cost=65536,   # 64 MB RAM
    parallelism=2,       # parallel threads
    hash_len=32,         # 256-bit output
    salt_len=16,         # 128-bit salt
)


def hash_passphrase(passphrase: str) -> str:
    """
    Hash a passphrase with Argon2id.
    Returns an encoded string including the algorithm, params, salt, and hash.
    Store this string in the database — it is self-describing.
    """
    return _hasher.hash(passphrase)


def verify_passphrase(stored_hash: str, passphrase: str) -> bool:
    """
    Verify a passphrase against a stored Argon2id hash.
    Returns True on match, False on mismatch.
    Raises no exceptions — all error paths return False.
    """
    try:
        return _hasher.verify(stored_hash, passphrase)
    except (VerifyMismatchError, VerificationError):
        return False


def derive_nonce() -> str:
    """
    Generate a cryptographically random 32-byte nonce, hex-encoded.
    Used in challenge-response to prevent passphrase hash replay attacks.
    Each session gets exactly one nonce; it is single-use.
    """
    return os.urandom(32).hex()


def derive_session_key(client_hash_hex: str, server_nonce_hex: str) -> bytes:
    """
    Re-derive the session key the client computed:
        session_key = HMAC-SHA256(client_hash, server_nonce)

    This key wraps all encrypted payloads sent by the client
    during identity verification — it cannot be replayed because
    the nonce is single-use and expires with the session.

    Args:
        client_hash_hex: hex-encoded client-side Argon2id hash
        server_nonce_hex: hex-encoded nonce issued by the server

    Returns:
        32-byte session key
    """
    client_hash = bytes.fromhex(client_hash_hex)
    server_nonce = bytes.fromhex(server_nonce_hex)
    return hmac.new(client_hash, server_nonce, hashlib.sha256).digest()