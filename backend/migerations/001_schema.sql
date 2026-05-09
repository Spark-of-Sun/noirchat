-- ─────────────────────────────────────────────────────────────────
-- 001_create_users.sql
-- Core users table for receiver accounts.
-- The passphrase is NEVER stored — only its Argon2id hash.
-- ─────────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username            TEXT NOT NULL UNIQUE,
    pass_hash           TEXT NOT NULL,              -- Argon2id encoded hash
    ack_code            TEXT NOT NULL               -- 4–10 char delivery confirmation code
                            CHECK (char_length(ack_code) BETWEEN 4 AND 10),
    balance             INTEGER NOT NULL DEFAULT 10
                            CHECK (balance >= 0),
    msg_ttl_days        SMALLINT NOT NULL DEFAULT 7
                            CHECK (msg_ttl_days BETWEEN 1 AND 90),
    time_window_start   SMALLINT                    -- UTC hour 0-23, NULL = always open
                            CHECK (time_window_start BETWEEN 0 AND 23),
    time_window_end     SMALLINT                    -- UTC hour 0-23, NULL = always open
                            CHECK (time_window_end BETWEEN 0 AND 23),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_username ON users(username);

-- ─────────────────────────────────────────────────────────────────
-- 002_create_messages.sql
-- Messages table — stores only ciphertext. Server is a blind carrier.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS messages (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receiver_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ciphertext              TEXT NOT NULL,          -- Base64 ChaCha20-Poly1305 blob
    sender_ephemeral_pubkey TEXT NOT NULL,          -- Base64 X25519 sender pubkey
    ack_token               TEXT NOT NULL,          -- HMAC-signed ack token
    is_read                 BOOLEAN NOT NULL DEFAULT FALSE,
    read_at                 TIMESTAMPTZ,            -- Soft delete timestamp
    expires_at              TIMESTAMPTZ NOT NULL,   -- Hard TTL
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Optimised for inbox queries: unread + not expired + by receiver
CREATE INDEX idx_messages_inbox
    ON messages(receiver_id, is_read, expires_at)
    WHERE is_read = FALSE;

-- Optimised for TTL worker: find expired or read rows efficiently
CREATE INDEX idx_messages_cleanup
    ON messages(expires_at, is_read);