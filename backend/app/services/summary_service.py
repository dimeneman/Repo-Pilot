"""
Summary Service — generates holistic repository summaries and architectural reviews.
"""
from __future__ import annotations

import re
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.file import File
from app.models.repository import Repository
from app.rag.llm_client import LLMClient
from app.rag.pipeline import sanitize_mermaid_diagram
from app.rag.prompt_builder import PromptBuilder
from app.retrieval.hybrid_search import HybridSearchService
from app.schemas.repository import RepoSummaryResponse

logger = get_logger(__name__)


class SummaryService:
    """Generates comprehensive codebase summaries with Mermaid diagrams."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
        self.hybrid_search = HybridSearchService()

    async def generate_summary(
        self,
        repo_id: uuid.UUID,
        db: AsyncSession,
    ) -> RepoSummaryResponse:
        """Analyze repository metadata and produce an architectural summary."""
        repo = await db.get(Repository, repo_id)
        if not repo:
            raise ValueError(f"Repository {repo_id} not found.")

        # 1. Fetch file paths
        stmt = select(File.path, File.language).where(File.repo_id == repo_id).limit(100)
        file_rows = (await db.execute(stmt)).all()
        file_paths = [r[0] for r in file_rows]

        # 2. Retrieve architectural chunks (e.g. README, config, main entrypoints)
        search_res = await self.hybrid_search.search(
            query="architecture main application setup server config overview router",
            repo_id=str(repo_id),
            db=db,
            top_k=8,
        )

        sample_chunks = [
            {
                "file_path": s.file_path,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "language": s.language,
                "content": s.content,
            }
            for s in search_res
        ]

        # 3. Build summary prompt
        system_prompt, user_prompt = PromptBuilder.build_summary_prompt(
            repo_name=f"{repo.owner}/{repo.name}",
            file_list=file_paths,
            language_stats=repo.language_stats or {},
            sample_chunks=sample_chunks,
        )

        # 4. Generate summary
        llm_res = await self.llm_client.generate(user_prompt, system_prompt)

        # Extract mermaid diagram
        mermaid_match = re.search(r"```mermaid\n([\s\S]*?)\n```", llm_res.content)
        mermaid_diagram = sanitize_mermaid_diagram(mermaid_match.group(1)) if mermaid_match else None

        tech_stack = list((repo.language_stats or {}).keys())

        return RepoSummaryResponse(
            answer=llm_res.content,
            mode="summary",
            tech_stack=tech_stack,
            file_tree_preview=file_paths[:30],
            mermaid_diagram=mermaid_diagram,
        )

