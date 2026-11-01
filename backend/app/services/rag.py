"""RAG service interface for API endpoints."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.pipeline import RAGPipeline, run_rag_pipeline
from app.services.summary_service import SummaryService
from app.schemas.chat import ChatResponse
from app.schemas.repository import RepoSummaryResponse


async def generate_summary(repo_id: uuid.UUID, db: AsyncSession) -> RepoSummaryResponse:
    """Generate repository summary."""
    service = SummaryService()
    return await service.generate_summary(repo_id, db)


__all__ = ["RAGPipeline", "run_rag_pipeline", "generate_summary"]

