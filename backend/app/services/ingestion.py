"""
Ingestion service and dispatcher for background repository indexing.
"""
from __future__ import annotations

from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.services.github_actions import GitHubActionsService
from app.workers.ingestion_worker import IngestionWorker, run_ingestion
from app.workers.queue import enqueue_job

logger = get_logger(__name__)


async def dispatch_ingestion_job(
    job_id: str,
    repo_id: str,
    repo_url: str,
    branch: Optional[str] = "main",
    access_token: Optional[str] = None,
) -> str:
    """Route the job to either GitHub Actions or the local worker queue.

    Returns:
        The runner type used ("github_actions" or "local").
    """
    runner_mode = (settings.INGESTION_RUNNER or "auto").lower()
    gh_service = GitHubActionsService()

    # Determine if we should attempt GitHub Actions dispatch
    should_use_github = False
    if runner_mode == "github_actions":
        should_use_github = True
    elif runner_mode == "auto" and gh_service.is_configured:
        should_use_github = True

    if should_use_github:
        try:
            logger.info(f"Dispatching job {job_id} to GitHub Actions workflow runner...")
            await gh_service.dispatch_ingest_job(
                job_id=job_id,
                repo_id=repo_id,
                repo_url=repo_url,
                branch=branch,
                access_token=access_token,
            )
            return "github_actions"
        except Exception as exc:
            if runner_mode == "github_actions":
                # In explicit github_actions mode, re-raise so caller fails fast
                raise exc
            logger.warning(
                f"GitHub Actions dispatch failed ({exc}). "
                "Falling back to local execution."
            )

    # Direct local in-process execution (zero queue / zero background daemon required)
    if runner_mode == "direct":
        import asyncio
        logger.info(f"Executing job {job_id} directly in local background task...")
        asyncio.create_task(
            IngestionWorker().process_job(job_id=job_id, access_token=access_token)
        )
        return "direct"

    # Local worker queue fallback (Redis or PostgreSQL polling daemon)
    logger.info(f"Enqueueing job {job_id} to local worker queue...")
    await enqueue_job(job_id, repo_id, access_token)
    return "local"


__all__ = ["IngestionWorker", "run_ingestion", "dispatch_ingestion_job", "GitHubActionsService"]
