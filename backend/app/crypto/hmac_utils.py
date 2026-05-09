"""
crypto/hmac_utils.py
─────────────────────
HMAC-SHA256 signing for delivery acknowledgement tokens.

The ack token proves to the sender that their message
was genuinely received and stored by the server — not spoofed.

Token format (before encoding):
    <message_id>:<timestamp_unix>:<ack_code>
Signed with the server's HMAC_ACK_KEY from Secrets Manager.

The ack code (set by the receiver) is encrypted with
the session key before delivery — the server never sends
the ack code in plaintext on any endpoint.
"""
import hmac
import hashlib
import base64
import time
from app.config import settings


def sign_ack_token(message_id: str, ack_code: str) -> str:
    """
    Create an HMAC-SHA256 signed ack token.

    Args:
        message_id: UUID of the stored message
        ack_code:   4–10 char receiver-defined confirmation string

    Returns:
        URL-safe base64 encoded token: "<payload_b64>.<signature_b64>"
    """
    timestamp = str(int(time.time()))
    payload = f"{message_id}:{timestamp}:{ack_code}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()

    sig = hmac.new(
        settings.hmac_ack_key_bytes,
        payload_b64.encode(),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode()

    return f"{payload_b64}.{sig_b64}"


def verify_ack_token(token: str) -> tuple[str, str] | None:
    """
    Verify an ack token and extract its payload.

    Returns:
        (message_id, ack_code) on success, None on invalid/tampered token.
    """
    try:
        payload_b64, sig_b64 = token.split(".")
        expected_sig = hmac.new(
            settings.hmac_ack_key_bytes,
            payload_b64.encode(),
            hashlib.sha256,
        ).digest()

        provided_sig = base64.urlsafe_b64decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload = base64.urlsafe_b64decode(payload_b64).decode()
        message_id, _timestamp, ack_code = payload.split(":", 2)
        return message_id, ack_code

    except Exception:
        return None