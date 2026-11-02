"""
Session cleanup service — cleans up stale demo sessions so ephemeral repositories
and related records do not grow indefinitely.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.repository import Repository

logger = get_logger("cleanup")


async def cleanup_stale_sessions(db: AsyncSession, max_age_hours: int = 12) -> int:
    """Delete repositories with session_id older than max_age_hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    try:
        stmt = select(Repository).where(
            Repository.session_id.isnot(None),
            Repository.created_at < cutoff,
        )
        result = await db.execute(stmt)
        stale_repos = result.scalars().all()
        if not stale_repos:
            return 0

        # Attempt vector cleanup if available
        try:
            from app.retrieval.vector_store import VectorStoreService
            vs = VectorStoreService()
        except Exception:
            vs = None

        count = 0
        for repo in stale_repos:
            if vs:
                try:
                    await vs.delete_by_repo(str(repo.id))
                except Exception:
                    pass
            await db.delete(repo)
            count += 1

        await db.commit()
        logger.info(f"Cleaned up {count} stale session repositories older than {max_age_hours}h.")
        return count
    except Exception as exc:
        logger.warning(f"Error during stale session cleanup: {exc}")
        return 0

