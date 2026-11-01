"""
File model — a single source file inside a tracked repository.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.chunk import Chunk
    from app.models.repository import Repository


class File(Base):
    """A single source file within a repository."""

    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    line_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    # ── Relationships ────────────────────────────────────────────────────
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="files",
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk", back_populates="file", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<File {self.path}>"
