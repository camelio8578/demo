"""ClipOS FastAPI application factory."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.base import engine
from app.routers import (
    creators,
    health,
    ingestion,
    monitored_sources,
    platform_accounts,
    rights_profiles,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate DB connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("database_connection_ok")
    except Exception as exc:
        logger.error("database_connection_failed", error=str(exc))
        raise
    yield
    # Shutdown
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ClipOS API",
        description="Autonomous short-form video clipping system",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(creators.router)
    app.include_router(rights_profiles.router)
    app.include_router(platform_accounts.router)
    app.include_router(monitored_sources.router)
    app.include_router(ingestion.router)

    return app


app = create_app()
