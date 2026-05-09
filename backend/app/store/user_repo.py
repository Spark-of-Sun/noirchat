"""
store/user_repo.py
"""
import asyncpg
from app.models.user import User


async def create_user(pool: asyncpg.Pool, user: User) -> User:
    await pool.execute(
        """
        INSERT INTO users (id, username, pass_hash, ack_code, balance,
                           msg_ttl_days, time_window_start, time_window_end,
                           created_at, updated_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        """,
        user.id, user.username, user.pass_hash, user.ack_code,
        user.balance, user.msg_ttl_days,
        user.time_window_start, user.time_window_end,
        user.created_at, user.updated_at,
    )
    return user


async def get_user_by_username(pool: asyncpg.Pool, username: str):
    row = await pool.fetchrow("SELECT * FROM users WHERE username = $1", username)
    return _row_to_user(row) if row else None


async def get_user_by_id(pool: asyncpg.Pool, user_id: str):
    row = await pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    return _row_to_user(row) if row else None


async def get_pass_hash_by_username(pool: asyncpg.Pool, username: str):
    row = await pool.fetchrow("SELECT pass_hash FROM users WHERE username = $1", username)
    return row["pass_hash"] if row else None


async def deduct_balance(pool: asyncpg.Pool, user_id: str, amount: int = 1) -> bool:
    result = await pool.fetchrow(
        """
        UPDATE users SET balance = balance - $2, updated_at = now()
        WHERE id = $1 AND balance >= $2
        RETURNING balance
        """,
        user_id, amount,
    )
    return result is not None


async def update_user_settings(pool, user_id, ack_code=None, msg_ttl_days=None,
                                time_window_start=None, time_window_end=None):
    await pool.execute(
        """
        UPDATE users SET
            ack_code = COALESCE($2, ack_code),
            msg_ttl_days = COALESCE($3, msg_ttl_days),
            time_window_start = $4,
            time_window_end = $5,
            updated_at = now()
        WHERE id = $1
        """,
        user_id, ack_code, msg_ttl_days, time_window_start, time_window_end,
    )


def _row_to_user(row) -> User:
    return User(
        id=str(row["id"]),
        username=row["username"],
        pass_hash=row["pass_hash"],
        ack_code=row["ack_code"],
        balance=row["balance"],
        msg_ttl_days=row["msg_ttl_days"],
        time_window_start=row["time_window_start"],
        time_window_end=row["time_window_end"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
