"""
crypto/keypair.py
─────────────────
X25519 elliptic-curve Diffie-Hellman key generation.

One ephemeral keypair is created per sender session.
Private keys NEVER leave the server unencrypted — they
are AES-GCM encrypted before being written to Redis.
"""
import base64
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption,
)


def generate_x25519_keypair() -> tuple[bytes, bytes]:
    """
    Generate an ephemeral X25519 keypair.

    Returns:
        (private_key_raw, public_key_raw) — both as raw 32-byte values.
    """
    private_key: X25519PrivateKey = X25519PrivateKey.generate()
    public_key: X25519PublicKey = private_key.public_key()

    private_bytes = private_key.private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()
    )
    public_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

    return private_bytes, public_bytes


def derive_shared_secret(server_private_raw: bytes, client_public_raw: bytes) -> bytes:
    """
    Perform X25519 ECDH key exchange.

    Args:
        server_private_raw: 32-byte raw server private key
        client_public_raw:  32-byte raw client public key

    Returns:
        32-byte shared secret (use as key material — do not use directly)
    """
    private_key = X25519PrivateKey.from_private_bytes(server_private_raw)
    client_public = X25519PublicKey.from_public_bytes(client_public_raw)
    return private_key.exchange(client_public)


def public_key_to_b64(public_key_raw: bytes) -> str:
    """Encode a raw 32-byte public key as URL-safe base64."""
    return base64.urlsafe_b64encode(public_key_raw).decode()


def b64_to_public_key_bytes(b64: str) -> bytes:
    """Decode a URL-safe base64 string to 32-byte public key bytes."""
    return base64.urlsafe_b64decode(b64)