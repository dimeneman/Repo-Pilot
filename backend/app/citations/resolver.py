"""
Citation resolver — converts retrieved chunks into verified source citations with exact lines and snippets.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.retrieval.vector_store import SearchResult
from app.schemas.chat import SourceCitation

logger = get_logger(__name__)


class CitationResolver:
    """Extracts, formats, and validates source citations for LLM answers."""

    @staticmethod
    def extract_snippet(content: str, max_lines: int = 10, max_chars: int = 800) -> str:
        """Extract a readable, concise snippet from the chunk content."""
        lines = content.strip().splitlines()
        trimmed = lines[:max_lines]
        snippet = "\n".join(trimmed)
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars] + "\n..."
        elif len(lines) > max_lines:
            snippet += "\n..."
        return snippet

    @classmethod
    async def resolve_citations(
        cls,
        search_results: List[SearchResult],
        db: Optional[AsyncSession] = None,
    ) -> List[SourceCitation]:
        """Convert a list of SearchResults into SourceCitation objects.

        If a database session is provided, optionally enriches chunk metadata.
        """
        citations: List[SourceCitation] = []
        seen = set()

        for item in search_results:
            key = f"{item.file_path}:{item.start_line}-{item.end_line}"
            if key in seen:
                continue
            seen.add(key)

            snippet = cls.extract_snippet(item.content)
            chunk_uuid = None
            try:
                chunk_uuid = uuid.UUID(item.chunk_id)
            except Exception:
                pass

            citations.append(
                SourceCitation(
                    file_path=item.file_path,
                    start_line=item.start_line,
                    end_line=item.end_line,
                    snippet=snippet,
                    relevance_score=item.score,
                    language=item.language,
                    chunk_id=chunk_uuid,
                )
            )

        return citations

    @classmethod
    def parse_llm_citations(cls, text: str) -> List[Dict[str, Any]]:
        """Extract citations referenced by the LLM in the format [FILE:path:L1-L2] or [path#L1-L2]."""
        citations = []
        # Pattern 1: [FILE:path:L10-L25]
        pattern1 = re.finditer(r"\[FILE:([^:]+):L(\d+)(?:-L?(\d+))?\]", text)
        for m in pattern1:
            file_path = m.group(1).strip()
            start = int(m.group(2))
            end = int(m.group(3)) if m.group(3) else start
            citations.append({"file_path": file_path, "start_line": start, "end_line": end})

        # Pattern 2: `path` lines X-Y or `path:X-Y`
        pattern2 = re.finditer(r"`([^`]+)`\s*(?:lines?\s*)?(\d+)(?:-(\d+))?", text)
        for m in pattern2:
            path = m.group(1).strip()
            if "/" in path or path.endswith((".py", ".ts", ".js", ".go", ".rs", ".java", ".md", ".json", ".yaml")):
                start = int(m.group(2))
                end = int(m.group(3)) if m.group(3) else start
                citations.append({"file_path": path, "start_line": start, "end_line": end})

        return citations

