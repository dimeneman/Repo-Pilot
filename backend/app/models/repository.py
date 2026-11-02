"""
Repository model — represents a GitHub repository tracked by RepoPilot.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.chunk import Chunk
    from app.models.file import File
    from app.models.job import Job
    from app.models.query import Query


class Repository(Base):
    """A tracked GitHub repository."""

    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Ingestion lifecycle: pending → cloning → parsing → indexing → ready | failed
    status: Mapped[str] = mapped_column(String(50), default="pending")

    file_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # e.g. {"Python": 45, "JavaScript": 30, …}
    language_stats: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # ── Relationships ────────────────────────────────────────────────────
    files: Mapped[list["File"]] = relationship(
        "File", back_populates="repository", cascade="all, delete-orphan",
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk", back_populates="repository", cascade="all, delete-orphan",
    )
    queries: Mapped[list["Query"]] = relationship(
        "Query", back_populates="repository", cascade="all, delete-orphan",
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="repository", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Repository {self.owner}/{self.name} [{self.status}]>"
