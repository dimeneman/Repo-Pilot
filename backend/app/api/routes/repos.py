"""
Repository CRUD and ingestion endpoints.
"""

from __future__ import annotations

import re
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession, Pagination, VectorStoreDep
from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.file import File
from app.models.job import Job
from app.models.repository import Repository
from app.schemas.repository import (
    RepoFileResponse,
    RepoIngestRequest,
    RepoListResponse,
    RepoResponse,
    RepoStatusResponse,
    RepoSummaryResponse,
)

router = APIRouter()
log = get_logger()


def _parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, name) from a GitHub URL.

    Args:
        url: Validated GitHub repository URL.

    Returns:
        Tuple of ``(owner, repo_name)``.

    Raises:
        ValueError: If the URL cannot be parsed.
    """
    match = re.match(r"https?://github\.com/([\w.\-]+)/([\w.\-]+)/?$", url)
    if not match:
        raise ValueError(f"Cannot parse GitHub URL: {url}")
    return match.group(1), match.group(2)


@router.post(
    "/ingest",
    response_model=RepoResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a GitHub repository",
)
async def ingest_repository(
    payload: RepoIngestRequest,
    db: DBSession,
    user: CurrentUser,
) -> RepoResponse:
    """Accept a GitHub URL, create a repository and job record, and enqueue
    for background worker processing.

    Returns immediately with status ``pending`` and the created ``job_id``.
    """
    owner, name = _parse_github_url(payload.url)

    # Check for duplicates
    existing = (
        await db.execute(
            select(Repository).where(Repository.url == payload.url)
        )
    ).scalar_one_or_none()

    if existing is not None:
        log.info(f"Repository {payload.url} already tracked (id={existing.id}, status={existing.status})")
        # If it failed previously or user is re-triggering, queue a new job
        if existing.status in ("failed", "pending"):
            existing.status = "pending"
            existing.error_message = None
            if payload.branch:
                existing.default_branch = payload.branch

            job = Job(
                repo_id=existing.id,
                job_type="ingest",
                status="pending",
                stage="pending",
                progress=0.0,
                step_description="Queued for ingestion",
                access_token=payload.access_token,
            )
            db.add(job)
            await db.commit()
            await db.refresh(existing)
            await db.refresh(job)

            from app.workers.queue import enqueue_job
            await enqueue_job(str(job.id), str(existing.id), payload.access_token)

            resp = RepoResponse.model_validate(existing)
            resp.job_id = job.id
            return resp

        return RepoResponse.model_validate(existing)

    repo = Repository(
        url=payload.url,
        name=name,
        owner=owner,
        default_branch=payload.branch,
        status="pending",
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    job = Job(
        repo_id=repo.id,
        job_type="ingest",
        status="pending",
        stage="pending",
        progress=0.0,
        step_description="Queued for ingestion",
        access_token=payload.access_token,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    log.info(f"Created repository {repo.id} and job {job.id} for {payload.url}")

    from app.workers.queue import enqueue_job
    await enqueue_job(str(job.id), str(repo.id), payload.access_token)

    resp = RepoResponse.model_validate(repo)
    resp.job_id = job.id
    return resp


@router.get(
    "",
    response_model=RepoListResponse,
    summary="List all repositories",
)
async def list_repositories(
    db: DBSession,
    pagination: Pagination,
) -> RepoListResponse:
    """Return a paginated list of all tracked repositories."""
    total_result = await db.execute(select(func.count(Repository.id)))
    total = total_result.scalar_one()

    result = await db.execute(
        select(Repository)
        .order_by(Repository.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    repos = result.scalars().all()

    return RepoListResponse(
        repositories=[RepoResponse.model_validate(r) for r in repos],
        total=total,
    )


@router.get(
    "/{repo_id}/status",
    response_model=RepoStatusResponse,
    summary="Get ingestion status",
)
async def get_repo_status(
    repo_id: uuid.UUID,
    db: DBSession,
) -> RepoStatusResponse:
    """Return the current ingestion status and progress for a repository."""
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )

    # Fetch the latest job for progress info
    job_result = await db.execute(
        select(Job)
        .where(Job.repo_id == repo_id)
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    job: Optional[Job] = job_result.scalar_one_or_none()

    return RepoStatusResponse(
        id=repo.id,
        status=repo.status,
        progress=job.progress if job else None,
        file_count=repo.file_count,
        chunk_count=repo.chunk_count,
        step_description=job.step_description if job else None,
        stage=job.stage if job else repo.status,
        job_id=job.id if job else None,
    )


@router.get(
    "/{repo_id}/files",
    response_model=list[RepoFileResponse],
    summary="List files in a repository",
)
async def list_repo_files(
    repo_id: uuid.UUID,
    db: DBSession,
    pagination: Pagination,
) -> list[RepoFileResponse]:
    """Return a paginated list of source files for the given repository."""
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )

    result = await db.execute(
        select(File)
        .where(File.repo_id == repo_id)
        .order_by(File.path)
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    files = result.scalars().all()
    return [RepoFileResponse.model_validate(f) for f in files]


@router.post(
    "/{repo_id}/reindex",
    response_model=RepoResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger re-indexing",
)
async def reindex_repository(
    repo_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
) -> RepoResponse:
    """Re-index an already-ingested repository in the background worker."""
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )

    repo.status = "pending"
    await db.commit()
    await db.refresh(repo)

    job = Job(
        repo_id=repo.id,
        job_type="reindex",
        status="pending",
        stage="pending",
        progress=0.0,
        step_description="Queued for reindexing",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    log.info(f"Created reindex job {job.id} for repo {repo.id}")

    from app.workers.queue import enqueue_job
    await enqueue_job(str(job.id), str(repo.id))

    resp = RepoResponse.model_validate(repo)
    resp.job_id = job.id
    return resp


@router.delete(
    "/{repo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a repository",
)
async def delete_repository(
    repo_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    vector_store: VectorStoreDep,
) -> None:
    """Delete a repository and all associated data (files, chunks, jobs,
    queries, and vector embeddings)."""
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )

    # Clean up vectors if the vector store is available
    if vector_store is not None:
        try:
            await vector_store.delete_by_repo(str(repo_id))  # type: ignore[union-attr]
        except Exception as exc:
            log.error(f"Failed to delete vectors for repo {repo_id}: {exc}")

    await db.delete(repo)
    await db.commit()
    log.info(f"Deleted repository {repo_id}")


@router.get(
    "/{repo_id}/summary",
    response_model=RepoSummaryResponse,
    summary="Get or generate a repository summary",
)
async def get_repo_summary(
    repo_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
) -> RepoSummaryResponse:
    """Generate (or return cached) a high-level summary for the repository.

    Uses the LLM to analyse the codebase structure, tech stack, and
    key features.
    """
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )

    if repo.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository is not ready (status={repo.status}). "
            "Please wait for ingestion to complete.",
        )

    # Attempt to call the services layer; return a stub if unavailable.
    try:
        from app.services.rag import generate_summary  # type: ignore[import-untyped]

        return await generate_summary(repo_id, db)
    except ImportError:
        log.warning("RAG service not available — returning placeholder summary.")
        return RepoSummaryResponse(
            answer=(
                f"Summary for **{repo.owner}/{repo.name}**: "
                f"{repo.file_count} files indexed, "
                f"{repo.chunk_count} chunks in vector store."
            ),
            mode="summary",
            tech_stack=list((repo.language_stats or {}).keys()),
        )
