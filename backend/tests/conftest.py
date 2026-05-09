import os
from pathlib import Path

# Load .env into environment for tests (strip inline comments)
root = Path(__file__).resolve().parents[1]
env_file = root / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        k, v = line.split('=', 1)
        v = v.split('#', 1)[0].strip()
        os.environ[k.strip()] = v

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
