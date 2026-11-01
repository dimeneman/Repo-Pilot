"""
Health-check endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.schemas.common import HealthResponse

router = APIRouter()
log = get_logger()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
)
async def health_check() -> HealthResponse:
    """Verify connectivity to the database and vector store, and report
    the loaded embedding model.
    """
    # ── Database check ───────────────────────────────────────────────────
    db_status = "unavailable"
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        log.error(f"Database health-check failed: {exc}")
        db_status = f"error: {exc}"

    # ── Vector store check ───────────────────────────────────────────────
    qdrant_status = "unavailable"
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(
            host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=5,
        )
        collections = client.get_collections()
        qdrant_status = f"connected ({len(collections.collections)} collections)"
    except Exception as exc:
        log.error(f"Qdrant health-check failed: {exc}")
        qdrant_status = f"error: {exc}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.VERSION,
        database=db_status,
        vector_store=qdrant_status,
        embedding_model=settings.EMBEDDING_MODEL,
    )
