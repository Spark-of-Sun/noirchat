"""
workers/ttl_cleanup.py
───────────────────────
Background task that permanently deletes expired or read messages.

Run this on a schedule (e.g. every hour via AWS EventBridge + Lambda,
or as a cron job inside the same container for simpler setups).

The two conditions for deletion:
  1. expires_at < now()  — TTL expired regardless of read status
  2. is_read = TRUE      — Receiver confirmed receipt; immediate cleanup eligible

This two-phase design prevents the read/delete race condition
where two concurrent requests both see the message before deletion.
"""
import asyncio
import logging
from app.store.database import create_pool, close_pool
from app.store.message_repo import hard_delete_expired
from app.config import settings

log = logging.getLogger(__name__)


async def run_cleanup() -> None:
    """
    Connect to the database, run the hard delete, then disconnect.
    Safe to run in a Lambda, a cron task, or a long-running loop.
    """
    pool = await create_pool()
    try:
        deleted = await hard_delete_expired(pool)
        log.info("ttl_cleanup completed", extra={"deleted_count": deleted})
    finally:
        await close_pool()


async def run_loop(interval_seconds: int = 3600) -> None:
    """
    Run cleanup on a loop with a fixed interval.
    Use this when running the worker as a sidecar process.
    """
    while True:
        try:
            await run_cleanup()
        except Exception as exc:
            log.error("ttl_cleanup_error", extra={"error": str(exc)})
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_cleanup())