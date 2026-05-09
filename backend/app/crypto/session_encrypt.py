"""
crypto/session_encrypt.py
──────────────────────────
AES-256-GCM encryption for Redis session blobs.

Why encrypt Redis values:
  If Redis is compromised mid-session, an attacker would
  find only opaque ciphertext — not private keys, not hashes.
  The decrypt key never touches Redis; it lives in Secrets Manager
  and is loaded into server memory at startup via settings.

Each encrypt call uses a fresh random 12-byte nonce.
Format stored in Redis: <nonce_hex>:<ciphertext_b64>
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import settings


def encrypt_session_data(plaintext: str) -> str:
    """
    AES-256-GCM encrypt a plaintext string for Redis storage.

    Args:
        plaintext: any JSON-serialisable string

    Returns:
        Colon-delimited string: "<nonce_hex>:<ciphertext_b64>"
    """
    key = settings.session_encrypt_key_bytes
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return f"{nonce.hex()}:{base64.b64encode(ciphertext).decode()}"


def decrypt_session_data(blob: str) -> str:
    """
    Decrypt an AES-256-GCM session blob retrieved from Redis.

    Args:
        blob: "<nonce_hex>:<ciphertext_b64>"

    Returns:
        Original plaintext string

    Raises:
        ValueError: if blob is malformed or decryption fails (tampered data)
    """
    try:
        nonce_hex, ct_b64 = blob.split(":", 1)
        nonce = bytes.fromhex(nonce_hex)
        ciphertext = base64.b64decode(ct_b64)
    except Exception as exc:
        raise ValueError("Malformed session blob") from exc

    key = settings.session_encrypt_key_bytes
    aesgcm = AESGCM(key)

    try:
        return aesgcm.decrypt(nonce, ciphertext, None).decode()
    except Exception as exc:
        raise ValueError("Session blob decryption failed — possible tampering") from exc