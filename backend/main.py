"""
main.py
────────
Application entry point.
Imports the app factory and starts uvicorn.

Usage:
    python main.py                  # development
    uvicorn main:app --host 0.0.0.0 # production (ECS/Docker)

    http://localhost:8000/docs # API docs (only in development)
"""
import logging
import uvicorn
from app.server import create_app
from app.config import settings

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=not settings.is_production,
        log_level=settings.log_level.lower(),
    )