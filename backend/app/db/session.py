"""
Async SQLAlchemy engine, session factory, and FastAPI dependency.

Uses the ``asyncpg`` driver for non-blocking database access.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger()

# ── Async engine ─────────────────────────────────────────────────────────
engine_kwargs: dict = {
    "echo": settings.DEBUG,
    "future": True,
}
if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 20,
        "max_overflow": 10,
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)


# ── Session factory ──────────────────────────────────────────────────────
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    The session is automatically closed when the request ends.

    Yields:
        An ``AsyncSession`` bound to the application engine.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all database tables defined by the SQLAlchemy metadata.

    This is called once during application startup (lifespan handler).
    For production migrations, use Alembic instead.
    """
    from app.db.base import Base  # noqa: F811 – imported here to avoid circular deps

    # Importing models ensures their tables are registered on Base.metadata
    import app.models  # noqa: F401

    log.info("Creating database tables …")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database tables created successfully.")
