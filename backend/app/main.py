"""
RepoPilot — Main FastAPI application entrypoint.
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import api_router
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import init_db
from app.retrieval.vector_store import VectorStoreService

logger = get_logger("repopilot")


def _build_cors_origins() -> list[str]:
    """Build the list of allowed CORS origins.

    Uses any configured origins from settings and always includes the
    localhost and Vercel frontend origins needed for local and production.
    """
    origins = list(settings.CORS_ORIGINS)

    default_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://repo-pilot-steel.vercel.app",
    ]

    for origin in default_origins:
        if origin not in origins:
            origins.append(origin)

    return origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown routines."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")

    # Ensure required data directories exist
    os.makedirs(settings.REPOS_DIR, exist_ok=True)
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)

    # Initialize relational database tables
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as exc:
        logger.error(f"Failed to initialize database: {exc}")

    # Ensure vector store collection exists
    try:
        vs = VectorStoreService()
        await vs.ensure_collection()
        logger.info(f"Vector store collection '{settings.QDRANT_COLLECTION}' ready.")
    except Exception as exc:
        logger.warning(f"Vector store initialization deferred: {exc}")

    # Reset any stale active jobs from previous crashes or container restarts
    try:
        from app.workers.ingestion_worker import IngestionWorker

        await IngestionWorker().reconcile_stale_jobs()
    except Exception as exc:
        logger.warning(f"Failed to reconcile stale jobs on startup: {exc}")

    # Clean up stale session demo repositories on startup
    try:
        from app.db.session import async_session_factory
        from app.services.cleanup import cleanup_stale_sessions

        async with async_session_factory() as session:
            await cleanup_stale_sessions(session, max_age_hours=12)
    except Exception as exc:
        logger.warning(f"Failed to clean up stale sessions on startup: {exc}")

    # Optional embedded background worker for single-process local development
    worker_task = None
    if settings.RUN_EMBEDDED_WORKER:
        from app.worker import run_worker_loop

        logger.info("Starting embedded background worker task...")
        worker_task = asyncio.create_task(run_worker_loop())

    yield

    if worker_task:
        logger.info("Stopping embedded background worker task...")
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="GitHub Repository RAG Assistant with source citations and codebase intelligence.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount all API routes under API prefix
app.include_router(api_router, prefix=settings.API_PREFIX)

# Also mount router at root so paths like /repos, /auth/github/url, /chat work seamlessly
if settings.API_PREFIX:
    app.include_router(api_router, include_in_schema=False)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")