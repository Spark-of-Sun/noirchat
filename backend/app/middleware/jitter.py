"""
middleware/jitter.py
─────────────────────
Random response delay (50–200ms) applied to all API responses.

Why: Without jitter, timing differences between "user found" and
"user not found" paths leak receiver existence even with identical
response bodies. With jitter, all paths are indistinguishable by timing.

This is a global ASGI middleware — no handler changes needed.
"""
import asyncio
import random
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class JitterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, min_ms: int = 50, max_ms: int = 200):
        super().__init__(app)
        self.min_s = min_ms / 1000
        self.max_s = max_ms / 1000

    async def dispatch(self, request: Request, call_next) -> Response:
        delay = random.uniform(self.min_s, self.max_s)
        await asyncio.sleep(delay)
        return await call_next(request)