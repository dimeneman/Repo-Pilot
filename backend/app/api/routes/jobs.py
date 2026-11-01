"""
Job status endpoints for background ingestion tasks.
"""

from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DBSession
from app.models.job import Job
from app.schemas.repository import JobResponse

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

