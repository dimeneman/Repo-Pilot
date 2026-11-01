"""
Job model — tracks long-running background tasks such as ingestion.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class Job(Base):
    """A background job (ingest / reindex) tied to a repository."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # "ingest" or "reindex"
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # pending → running → completed | failed
    status: Mapped[str] = mapped_column(String(50), default="pending")

    progress: Mapped[float] = mapped_column(Float, default=0.0)
    total_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_step: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    step_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    # ── Relationships ────────────────────────────────────────────────────
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="jobs",
    )

    def __repr__(self) -> str:
        return f"<Job {self.id} type={self.job_type} status={self.status}>"
