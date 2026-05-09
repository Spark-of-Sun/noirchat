"""
app/server.py
─────────────
FastAPI application factory.

All middleware, routers, and lifespan hooks are registered here.
The app object is imported by main.py (and by tests).
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.store.database import create_pool, close_pool
from app.store.redis_store import create_redis, close_redis
from app.middleware.jitter import JitterMiddleware
from app.middleware.logger import RequestLoggerMiddleware
from app.api import session, identity, message, auth

# Global rate limiter (backed by Redis in production)
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup / shutdown hooks.
    Runs once at startup: connects to Postgres and Redis.
    Runs once at shutdown: closes all connections gracefully.
    """
    await create_pool()
    await create_redis()
    yield
    await close_pool()
    await close_redis()


def create_app() -> FastAPI:
    """
    Build and return the FastAPI application.
    Called by main.py and by test fixtures.
    """
    app = FastAPI(
        title="Noirchat API",
        version="1.0.0",
        description="Secure one-way encrypted messaging API",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # ── Rate limiting ──────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ───────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ── Custom middleware (applied last = outermost) ───────────────
    app.add_middleware(JitterMiddleware, min_ms=50, max_ms=200)
    app.add_middleware(RequestLoggerMiddleware)

    # ── Routers ────────────────────────────────────────────────────
    app.include_router(session.router)
    app.include_router(identity.router)
    app.include_router(message.router)
    app.include_router(auth.router)

    @app.get("/health", tags=["health"])
    async def health_check():
        """Liveness probe for load balancer health checks."""
        return {"status": "ok"}

    return app