"""
Chat / RAG query endpoints.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession, Pagination, VectorStoreDep
from app.core.logging import get_logger
from app.models.query import Query
from app.models.repository import Repository
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    SourceCitation,
)

router = APIRouter()
log = get_logger()


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question about a repository",
)
async def chat(
    payload: ChatRequest,
    db: DBSession,
    vector_store: VectorStoreDep,
    user: CurrentUser,
) -> ChatResponse:
    """Run the RAG pipeline: retrieve relevant chunks, build a prompt,
    call the LLM, persist the exchange, and return the answer with
    source citations.
    """
    start_ms = int(time.time() * 1000)

    # Validate repository exists and is ready
    repo = await db.get(Repository, payload.repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {payload.repo_id} not found.",
        )
    if repo.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Repository is not ready for queries (status={repo.status}). "
                "Please wait for ingestion to complete."
            ),
        )

    # Delegate to the RAG service layer
    try:
        from app.services.rag import run_rag_pipeline  # type: ignore[import-untyped]

        result = await run_rag_pipeline(
            repo_id=str(payload.repo_id),
            question=payload.question,
            mode=payload.mode,
            top_k=payload.top_k,
            include_sources=payload.include_sources,
            db=db,
        )
        return result
    except ImportError:
        log.warning("RAG service not yet available — returning placeholder.")

    elapsed_ms = int(time.time() * 1000) - start_ms

    # Persist query even if the RAG service isn't wired up
    query_record = Query(
        repo_id=payload.repo_id,
        user_question=payload.question,
        response_text="The RAG pipeline is not yet configured.",
        sources=None,
        mode=payload.mode,
        processing_time_ms=elapsed_ms,
    )
    db.add(query_record)
    await db.commit()
    await db.refresh(query_record)

    return ChatResponse(
        answer="The RAG pipeline is not yet configured. Please set up the services layer.",
        sources=[],
        mode=payload.mode,
        query_id=query_record.id,
        processing_time_ms=elapsed_ms,
    )


@router.get(
    "/history/{repo_id}",
    response_model=ChatHistoryResponse,
    summary="Get chat history for a repository",
)
async def get_chat_history(
    repo_id: uuid.UUID,
    db: DBSession,
    pagination: Pagination,
) -> ChatHistoryResponse:
    """Return paginated chat history for the specified repository."""
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )

    total_result = await db.execute(
        select(func.count(Query.id)).where(Query.repo_id == repo_id)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(Query)
        .where(Query.repo_id == repo_id)
        .order_by(Query.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    queries = result.scalars().all()

    chat_responses: list[ChatResponse] = []
    for q in queries:
        sources: list[SourceCitation] = []
        if q.sources:
            sources = [SourceCitation(**s) for s in q.sources]

        chat_responses.append(
            ChatResponse(
                answer=q.response_text,
                sources=sources,
                mode=q.mode,
                query_id=q.id,
                model_used=q.model_used,
                processing_time_ms=q.processing_time_ms,
            )
        )

    return ChatHistoryResponse(queries=chat_responses, total=total)
