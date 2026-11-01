"""
RepoPilot — Main FastAPI application entrypoint.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import api_router
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import init_db
from app.retrieval.vector_store import VectorStoreService

logger = get_logger("repopilot")



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

    # Optional embedded background worker for single-process local development
    worker_task = None
    if settings.RUN_EMBEDDED_WORKER:
        import asyncio
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routes under API prefix
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")
