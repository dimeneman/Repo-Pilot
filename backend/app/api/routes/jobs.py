"""
Job status endpoints for background ingestion tasks.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy import select

from app.api.deps import DBSession
from app.core.config import settings
from app.models.job import Job
from app.models.repository import Repository
from app.schemas.repository import JobResponse, JobUpdateStatusRequest

router = APIRouter()


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get background job status",
)
async def get_job_status(
    job_id: uuid.UUID,
    db: DBSession,
) -> JobResponse:
    """Fetch status and progress for a specific background ingestion job."""
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )
    return JobResponse.model_validate(job)


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
    summary="Update job progress and status",
)
async def update_job_status(
    job_id: uuid.UUID,
    payload: JobUpdateStatusRequest,
    db: DBSession,
    x_ingestion_secret: Optional[str] = Header(None, alias="X-Ingestion-Secret"),
) -> JobResponse:
    """Allow external runners (e.g. GitHub Actions) or scripts to update job progress."""
    if (
        settings.SECRET_KEY
        and settings.SECRET_KEY != "change-me-in-production-use-openssl-rand-hex-32"
    ):
        if x_ingestion_secret != settings.SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid ingestion secret.",
            )

    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    now = datetime.now(timezone.utc)
    if payload.status is not None:
        job.status = payload.status
        if payload.status == "running" and not job.started_at:
            job.started_at = now
        elif payload.status in ("completed", "failed"):
            job.completed_at = now
    if payload.stage is not None:
        job.stage = payload.stage
    if payload.progress is not None:
        job.progress = payload.progress
    if payload.step_description is not None:
        job.step_description = payload.step_description
    if payload.error_message is not None:
        job.error_message = payload.error_message

    job.updated_at = now

    # Propagate to Repository
    repo = await db.get(Repository, job.repo_id)
    if repo:
        if payload.status == "completed":
            repo.status = "ready"
            repo.error_message = None
            repo.last_indexed_at = now
        elif payload.status == "failed":
            repo.status = "failed"
            repo.error_message = (
                payload.error_message or "Ingestion failed in external runner."
            )
        elif payload.status == "running":
            if payload.stage in ("cloning", "parsing", "indexing"):
                repo.status = payload.stage
        repo.updated_at = now

    await db.commit()
    await db.refresh(job)
    return JobResponse.model_validate(job)

