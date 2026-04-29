"""FastAPI application factory for Proceeds Navigator."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from proceeds_navigator import __version__
from proceeds_navigator.api.deps import get_db
from proceeds_navigator.api.routers import leads, cases, documents, export
from proceeds_navigator.api.schemas import HealthResponse, ScrapeRunSummary
from proceeds_navigator.db.models import Case, Lead, ScrapeRun
from proceeds_navigator.db.session import init_db

log = structlog.get_logger()


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        init_db()
        log.info("proceeds_navigator_started", version=__version__)
        yield

    app = FastAPI(
        title="Proceeds Navigator API",
        description="California excess proceeds monitoring platform — internal operations API",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    origins = [
        o.strip()
        for o in os.getenv("API_CORS_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers — all under /api/v1
    prefix = "/api/v1"
    app.include_router(leads.router, prefix=prefix)
    app.include_router(cases.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(export.router, prefix=prefix)

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
    def health(db: Session = Depends(get_db)) -> HealthResponse:
        lead_count = db.scalar(select(func.count(Lead.id))) or 0
        case_count = db.scalar(select(func.count(Case.id))) or 0
        subq = (
            select(ScrapeRun.county, func.max(ScrapeRun.started_at).label("max_started"))
            .group_by(ScrapeRun.county)
            .subquery()
        )
        recent_runs = db.scalars(
            select(ScrapeRun).join(
                subq,
                (ScrapeRun.county == subq.c.county)
                & (ScrapeRun.started_at == subq.c.max_started),
            )
        ).all()
        return HealthResponse(
            status="ok",
            version=__version__,
            lead_count=lead_count,
            case_count=case_count,
            last_scrape_runs=[ScrapeRunSummary.model_validate(r) for r in recent_runs],
        )

    return app


app = create_app()
