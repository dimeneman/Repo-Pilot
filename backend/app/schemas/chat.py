"""
Pydantic v2 schemas for the chat / RAG endpoints.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload for the RAG chat endpoint."""

    repo_id: UUID = Field(..., description="Repository to query against.")
    question: str = Field(
        ...,
        min_length=3,
        max_length=5000,
        description="The user's natural-language question.",
    )
    mode: str = Field(
        default="chat",
        description=(
            "Query mode: chat, summary, api_discovery, readme, "
            "bug_scan, or architecture."
        ),
    )
    include_sources: bool = Field(
        default=True,
        description="Whether to include source citations in the response.",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of relevant chunks to retrieve from the vector store.",
    )


class SourceCitation(BaseModel):
    """A single source citation referencing a code chunk."""

    file_path: str
    start_line: int
    end_line: int
    snippet: str
    relevance_score: Optional[float] = None
    language: Optional[str] = None
    chunk_id: Optional[UUID] = None


class ChatResponse(BaseModel):
    """Response from the RAG chat endpoint."""

    answer: str
    sources: list[SourceCitation] = Field(default_factory=list)
    mode: str
    query_id: UUID
    model_used: Optional[str] = None
    processing_time_ms: Optional[int] = None
    mermaid_diagram: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """Paginated list of past chat interactions for a repository."""

    queries: list[ChatResponse]
    total: int
