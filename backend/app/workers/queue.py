"""
Job queue service supporting Redis with automatic database fallback.

Ensures that background ingestion jobs are durably enqueued and processed
outside of the web request lifecycle, in both local development and Render.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import select, update

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.job import Job
from app.models.repository import Repository

logger = get_logger(__name__)

INGESTION_QUEUE_KEY = "repopilot:queue:ingestion"


class JobQueue:
    """Manages job enqueuing and dequeuing using Redis with database fallback."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis_client = None
        self._redis_available: Optional[bool] = None

    async def _get_redis(self):
        """Get or initialize async Redis client."""
        if self._redis_available is False:
            return None

        if self._redis_client is None:
            try:
                import redis.asyncio as aioredis
                client = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                    socket_timeout=3.0,
                )
                await client.ping()
                self._redis_client = client
                self._redis_available = True
                logger.info(f"Connected to Redis queue at {self.redis_url}")
            except Exception as exc:
                logger.debug(f"Redis queue unavailable ({exc}). Using database job polling.")
                self._redis_available = False
                self._redis_client = None

        return self._redis_client

    async def enqueue_job(
        self,
        job_id: str,
        repo_id: str,
        access_token: Optional[str] = None,
    ) -> bool:
        """Enqueue an ingestion job.
        
        The job record is already durably committed to the database.
        If Redis is reachable, we also push a notification message so
        active workers are immediately woken up.
        """
        payload = {
            "job_id": str(job_id),
            "repo_id": str(repo_id),
            "access_token": access_token,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        }

        redis = await self._get_redis()
        if redis:
            try:
                await redis.rpush(INGESTION_QUEUE_KEY, json.dumps(payload))
                logger.info(f"Enqueued job {job_id} to Redis queue.")
                return True
            except Exception as exc:
                logger.warning(f"Failed to push job {job_id} to Redis: {exc}. Job remains queued in DB.")
                self._redis_available = False

        # If Redis is unavailable, the job remains in PostgreSQL with status="pending"
        logger.info(f"Job {job_id} queued in database for worker pickup.")
        return True

    async def dequeue_job(self, timeout: int = 2) -> Optional[Dict[str, Any]]:
        """Fetch the next available pending job.
        
        1. Checks Redis queue first for immediate notifications.
        2. Fallback: Checks PostgreSQL for any job with status='pending',
           atomically claiming it to prevent duplicate execution across workers.
        """
        redis = await self._get_redis()
        if redis:
            try:
                item = await redis.blpop(INGESTION_QUEUE_KEY, timeout=timeout)
                if item:
                    _, data_str = item
                    data = json.loads(data_str)
                    return data
            except Exception as exc:
                logger.debug(f"Redis pop failed ({exc}), falling back to database check.")
                self._redis_available = False

        # Database polling fallback: atomically find and claim next pending job
        async with async_session_factory() as db:
            result = await db.execute(
                select(Job)
                .where(Job.status == "pending")
                .order_by(Job.created_at.asc())
                .limit(1)
            )
            job = result.scalar_one_or_none()
            if not job:
                return None

            # Atomically claim the job
            claim_result = await db.execute(
                update(Job)
                .where(Job.id == job.id, Job.status == "pending")
                .values(
                    status="running",
                    stage="cloning",
                    started_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()

            if claim_result.rowcount > 0:
                logger.info(f"Claimed pending job {job.id} directly from database.")
                return {
                    "job_id": str(job.id),
                    "repo_id": str(job.repo_id),
                    "access_token": job.access_token,
                }

        return None


# Global queue instance and helper functions
default_queue = JobQueue()


async def enqueue_job(job_id: str, repo_id: str, access_token: Optional[str] = None) -> bool:
    """Helper to enqueue a job via the default queue."""
    return await default_queue.enqueue_job(job_id, repo_id, access_token)


async def dequeue_job(timeout: int = 2) -> Optional[Dict[str, Any]]:
    """Helper to dequeue the next job via the default queue."""
    return await default_queue.dequeue_job(timeout)

