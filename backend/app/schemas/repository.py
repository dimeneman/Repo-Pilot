"""
Pydantic v2 schemas for repository-related requests and responses.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Request schemas ──────────────────────────────────────────────────────

class RepoIngestRequest(BaseModel):
    """Payload to trigger repository ingestion."""

    url: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="HTTPS GitHub repository URL.",
        examples=["https://github.com/owner/repo"],
    )
    branch: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Branch to index (optional; automatically detects remote default branch like main/master if omitted).",
    )
    access_token: Optional[str] = Field(
        default=None,
        description="Optional GitHub personal access token or OAuth token for authentication / private repo cloning.",
    )

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        """Ensure the URL looks like a valid GitHub repository."""
        pattern = r"^https?://github\.com/[\w.\-]+/[\w.\-]+/?$"
        if not re.match(pattern, v.rstrip("/")):
            raise ValueError(
                "URL must be a valid GitHub repository URL "
                "(e.g. https://github.com/owner/repo)"
            )
        return v.rstrip("/")


# ── Response schemas ─────────────────────────────────────────────────────

class RepoResponse(BaseModel):
    """Full representation of a repository record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    name: str
    owner: str
    default_branch: str
    description: Optional[str] = None
    status: str
    file_count: int
    chunk_count: int
    language_stats: Optional[dict] = None
    last_indexed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    job_id: Optional[UUID] = None


class RepoStatusResponse(BaseModel):
    """Lightweight status / progress view of a repository."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    progress: Optional[float] = None
    file_count: int
    chunk_count: int
    step_description: Optional[str] = None
    stage: Optional[str] = None
    job_id: Optional[UUID] = None


class JobResponse(BaseModel):
    """Representation of an ingestion / reindexing background job."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    repo_id: UUID
    job_type: str
    status: str
    stage: Optional[str] = None
    progress: float = 0.0
    step_description: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class JobUpdateStatusRequest(BaseModel):
    """Payload for updating job status/progress from an external runner or API."""

    status: Optional[str] = None  # "pending", "running", "completed", "failed"
    stage: Optional[str] = None   # "cloning", "parsing", "chunking", "embeddings", "indexing", "done", "failed"
    progress: Optional[float] = None
    step_description: Optional[str] = None
    error_message: Optional[str] = None


class RepoFileResponse(BaseModel):
    """Summary of a single file within a repository."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    path: str
    language: Optional[str] = None
    size: int
    line_count: int


class RepoListResponse(BaseModel):
    """Paginated list of repositories."""

    repositories: list[RepoResponse]
    total: int


class RepoSummaryResponse(BaseModel):
    """Extended summary produced by the LLM for a repository."""

    answer: str
    sources: list = Field(default_factory=list)
    mode: str = "summary"
    query_id: Optional[UUID] = None
    model_used: Optional[str] = None
    processing_time_ms: Optional[int] = None
    mermaid_diagram: Optional[str] = None

    # Extra summary-specific fields
    tech_stack: Optional[list[str]] = None
    folder_structure: Optional[str] = None
    key_features: Optional[list[str]] = None
    dependencies: Optional[list[str]] = None
