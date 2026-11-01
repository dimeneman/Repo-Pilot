"""
Repository Service — business logic for repository records, files, and lifecycle.
"""
from __future__ import annotations

import re
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.file import File
from app.models.job import Job
from app.models.repository import Repository
from app.retrieval.vector_store import VectorStoreService
from app.schemas.repository import RepoIngestRequest

logger = get_logger(__name__)


class RepositoryService:
    """Manages repository records and database operations."""

    @staticmethod
    def parse_github_url(url: str) -> Tuple[str, str]:
        """Extract (owner, name) from a GitHub repository URL."""
        cleaned = url.strip().rstrip("/")
        if cleaned.endswith(".git"):
            cleaned = cleaned[:-4]
        match = re.search(r"github\.com[/:]([\w.\-]+)/([\w.\-]+)", cleaned)
        if not match:
            raise ValueError(f"Invalid GitHub repository URL: {url}")
        return match.group(1), match.group(2)

    @classmethod
    async def create_repository(
        cls,
        db: AsyncSession,
        request: RepoIngestRequest,
    ) -> Repository:
        """Create a new repository record if not already tracked."""
        owner, name = cls.parse_github_url(request.url)

        # Check existing
        existing = (
            await db.execute(select(Repository).where(Repository.url == request.url))
        ).scalar_one_or_none()

        if existing:
            return existing

        repo = Repository(
            url=request.url,
            name=name,
            owner=owner,
            default_branch=request.branch or "main",
            status="pending",
        )
        db.add(repo)
        await db.commit()
        await db.refresh(repo)
        return repo

    @staticmethod
    async def get_repository(db: AsyncSession, repo_id: uuid.UUID) -> Optional[Repository]:
        """Retrieve repository by UUID."""
        return await db.get(Repository, repo_id)

    @staticmethod
    async def list_repositories(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Repository], int]:
        """List repositories with pagination."""
        total_q = await db.execute(select(func.count(Repository.id)))
        total = total_q.scalar_one()

        stmt = (
            select(Repository)
            .order_by(Repository.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        repos = (await db.execute(stmt)).scalars().all()
        return list(repos), total

    @staticmethod
    async def get_repo_files(db: AsyncSession, repo_id: uuid.UUID) -> List[File]:
        """Retrieve all indexed files for a repository."""
        stmt = (
            select(File)
            .where(File.repo_id == repo_id)
            .order_by(File.path.asc())
        )
        files = (await db.execute(stmt)).scalars().all()
        return list(files)

    @staticmethod
    async def delete_repository(
        db: AsyncSession,
        repo_id: uuid.UUID,
        vector_store: Optional[VectorStoreService] = None,
    ) -> bool:
        """Delete repository and purge all associated chunks from DB and vector store."""
        repo = await db.get(Repository, repo_id)
        if not repo:
            return False

        if vector_store:
            try:
                await vector_store.delete_by_repo(str(repo_id))
            except Exception as exc:
                logger.error(f"Failed deleting vectors for {repo_id}: {exc}")

        await db.delete(repo)
        await db.commit()
        return True

