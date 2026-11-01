"""
Source-code chunk retrieval endpoint.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession
from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.file import File

router = APIRouter()
log = get_logger()


class ChunkDetailResponse(dict):
    """Ad-hoc response model for a chunk with surrounding context.

    We use a plain dict-like so we can freely add contextual fields
    without a rigid schema — the service layer may enrich this later.
    """

    pass


@router.get(
    "/{chunk_id}",
    summary="Get a chunk with surrounding context",
)
async def get_chunk_detail(
    chunk_id: uuid.UUID,
    db: DBSession,
) -> dict:
    """Return the full content of a chunk along with its file metadata
    and surrounding chunks for context.
    """
    chunk = (
        await db.execute(
            select(Chunk)
            .where(Chunk.id == chunk_id)
            .options(selectinload(Chunk.file))
        )
    ).scalar_one_or_none()

    if chunk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk {chunk_id} not found.",
        )

    # Fetch surrounding chunks from the same file for context
    surrounding = (
        await db.execute(
            select(Chunk)
            .where(
                Chunk.file_id == chunk.file_id,
                Chunk.chunk_index.between(
                    max(chunk.chunk_index - 1, 0),
                    chunk.chunk_index + 1,
                ),
            )
            .order_by(Chunk.chunk_index)
        )
    ).scalars().all()

    return {
        "chunk": {
            "id": str(chunk.id),
            "file_id": str(chunk.file_id),
            "repo_id": str(chunk.repo_id),
            "chunk_index": chunk.chunk_index,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content": chunk.content,
            "chunk_type": chunk.chunk_type,
            "token_count": chunk.token_count,
        },
        "file": {
            "id": str(chunk.file.id),
            "path": chunk.file.path,
            "language": chunk.file.language,
            "size": chunk.file.size,
            "line_count": chunk.file.line_count,
        } if chunk.file else None,
        "surrounding_chunks": [
            {
                "id": str(s.id),
                "chunk_index": s.chunk_index,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "content": s.content,
            }
            for s in surrounding
            if s.id != chunk.id
        ],
    }
