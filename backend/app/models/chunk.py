"""
Chunk model — a text chunk of a source file stored for RAG retrieval.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.file import File
    from app.models.repository import Repository


class Chunk(Base):
    """A code/doc/config chunk produced during ingestion.

    Each chunk maps to one embedding vector stored in the vector database,
    referenced by ``embedding_id``.
    """

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Qdrant point ID (string representation of the UUID used in the vector DB)
    embedding_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True,
    )

    token_count: Mapped[int] = mapped_column(Integer, default=0)

    # "code", "doc", or "config"
    chunk_type: Mapped[str] = mapped_column(String(20), default="code")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    # ── Relationships ────────────────────────────────────────────────────
    file: Mapped["File"] = relationship("File", back_populates="chunks")
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="chunks",
    )

    def __repr__(self) -> str:
        return (
            f"<Chunk {self.chunk_index} of file={self.file_id} "
            f"[{self.start_line}–{self.end_line}]>"
        )
