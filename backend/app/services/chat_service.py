"""
Chat Service — handles user queries, chat history, and conversational interactions.
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.query import Query
from app.rag.pipeline import RAGPipeline
from app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse

logger = get_logger(__name__)


class ChatService:
    """Manages chat queries and history."""

    def __init__(self, pipeline: Optional[RAGPipeline] = None):
        self.pipeline = pipeline or RAGPipeline()

    async def answer_question(
        self,
        db: AsyncSession,
        request: ChatRequest,
    ) -> ChatResponse:
        """Process a question using the RAG pipeline."""
        return await self.pipeline.run(
            repo_id=str(request.repo_id),
            question=request.question,
            db=db,
            mode=request.mode,
            top_k=request.top_k,
            include_sources=request.include_sources,
        )

    @staticmethod
    async def get_chat_history(
        db: AsyncSession,
        repo_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> ChatHistoryResponse:
        """Fetch past queries for a given repository."""
        total_q = await db.execute(
            select(func.count(Query.id)).where(Query.repo_id == repo_id)
        )
        total = total_q.scalar_one()

        stmt = (
            select(Query)
            .where(Query.repo_id == repo_id)
            .order_by(Query.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        records = (await db.execute(stmt)).scalars().all()

        responses: List[ChatResponse] = []
        for r in records:
            sources = r.sources or []
            responses.append(
                ChatResponse(
                    answer=r.response_text,
                    sources=sources,
                    mode=r.mode or "chat",
                    query_id=r.id,
                    model_used=r.model_used,
                    processing_time_ms=r.processing_time_ms,
                )
            )

        return ChatHistoryResponse(queries=responses, total=total)

