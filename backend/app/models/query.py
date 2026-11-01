"""
Query model — persisted record of every user question and RAG response.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class Query(Base):
    """A single RAG question / answer exchange."""

    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_question: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)

    # List of citation dicts: [{file_path, start_line, end_line, snippet, …}]
    sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # chat | summary | api_discovery | readme | bug_scan | architecture
    mode: Mapped[str] = mapped_column(String(50), default="chat")

    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    # ── Relationships ────────────────────────────────────────────────────
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="queries",
    )

    def __repr__(self) -> str:
        return f"<Query {self.id} mode={self.mode}>"
