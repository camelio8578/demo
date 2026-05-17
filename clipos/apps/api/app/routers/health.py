"""Health check endpoint."""

import redis as redis_client
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    db_ok = False
    redis_ok = False

    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error("health_db_check_failed", error=str(exc))

    try:
        r = redis_client.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        redis_ok = True
    except Exception as exc:
        logger.error("health_redis_check_failed", error=str(exc))

    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "db_ok": db_ok,
        "redis_ok": redis_ok,
        "version": "0.1.0",
    }
