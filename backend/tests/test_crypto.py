import os
from pathlib import Path
import sys

# Load .env into environment for settings
p = Path(__file__).resolve().parents[1] / ".env"
if p.exists():
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        k, v = line.split('=', 1)
        # Strip inline comments after the value
        v = v.split('#', 1)[0].strip()
        os.environ[k.strip()] = v

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Ensure secret keys are valid hex strings for tests (override placeholders)
def _ensure_hex_env(key: str):
    v = os.environ.get(key)
    try:
        if v is None:
            raise ValueError
        bytes.fromhex(v)
    except Exception:
        os.environ[key] = 'a' * 64

_ensure_hex_env('SESSION_ENCRYPT_KEY')
_ensure_hex_env('HMAC_ACK_KEY')

from app.crypto.hashing import hash_passphrase, verify_passphrase, derive_nonce, derive_session_key
from app.crypto.hmac_utils import sign_ack_token, verify_ack_token
from app.crypto.session_encrypt import encrypt_session_data, decrypt_session_data


def test_hash_and_verify():
    pw = 'test-password-123'
    h = hash_passphrase(pw)
    assert verify_passphrase(h, pw) is True
    assert verify_passphrase(h, pw + 'x') is False


def test_derive_session_key_and_nonce():
    client_hash_hex = os.urandom(32).hex()
    server_nonce_hex = derive_nonce()
    sk = derive_session_key(client_hash_hex, server_nonce_hex)
    assert isinstance(sk, (bytes, bytearray))
    assert len(sk) == 32


def test_encrypt_decrypt_roundtrip():
    # Ensure a valid session key is present in env for AES
    if os.environ.get('SESSION_ENCRYPT_KEY') is None:
        os.environ['SESSION_ENCRYPT_KEY'] = 'a' * 64
    plaintext = 'hello world'
    blob = encrypt_session_data(plaintext)
    out = decrypt_session_data(blob)
    assert out == plaintext


def test_ack_token_sign_verify():
    if os.environ.get('HMAC_ACK_KEY') is None:
        os.environ['HMAC_ACK_KEY'] = 'b' * 64
    tok = sign_ack_token('msg-1', 'ACK1')
    out = verify_ack_token(tok)
    assert out is not None
    assert out[0] == 'msg-1'
    assert out[1] == 'ACK1'
