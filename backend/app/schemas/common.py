"""
Shared / common Pydantic v2 schemas used across the API.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health-check response payload."""

    status: str = Field(..., description="Overall application status.")
    version: str
    database: str = Field(..., description="Database connectivity status.")
    vector_store: str = Field(..., description="Qdrant connectivity status.")
    embedding_model: str = Field(..., description="Loaded embedding model name.")


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str
    error_code: Optional[str] = None


class PaginationParams(BaseModel):
    """Common pagination query parameters."""

    skip: int = Field(default=0, ge=0, description="Number of records to skip.")
    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum records to return.",
    )
