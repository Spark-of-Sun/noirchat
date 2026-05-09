"""
config.py
─────────
Single source of truth for all environment-driven settings.
Access anywhere with: from app.config import settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Server ──────────────────────────────────────────────────
    app_env: str = "development"
    app_port: int = 8000
    log_level: str = "INFO"
    allowed_origins: str = "http://localhost:5173"
    # ── Database ─────────────────────────────────────────────────
    database_url: str

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Crypto secrets ───────────────────────────────────────────
    session_encrypt_key: str          # hex-encoded 32-byte key for AES-GCM session blobs
    hmac_ack_key: str                 # hex-encoded 32-byte key for HMAC ack tokens

    # ── JWT ──────────────────────────────────────────────────────
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ── Rate limiting ────────────────────────────────────────────
    rate_limit_per_minute: int = 30

    # ── Session TTL ──────────────────────────────────────────────
    session_ttl_seconds: int = 300    # ephemeral keypair lives 5 min max

    # ── Message TTL ──────────────────────────────────────────────
    default_msg_ttl_days: int = 7

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def session_encrypt_key_bytes(self) -> bytes:
        return bytes.fromhex(self.session_encrypt_key)

    @property
    def hmac_ack_key_bytes(self) -> bytes:
        return bytes.fromhex(self.hmac_ack_key)
    
    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance — instantiated once at startup.
    Use get_settings() rather than importing settings directly
    so tests can override with dependency injection.
    """
    return Settings()


settings = get_settings()