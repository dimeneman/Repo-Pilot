"""
RAG Pipeline — end-to-end question answering and repository intelligence orchestrator.
"""
from __future__ import annotations

import re
import time
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.citations.resolver import CitationResolver
from app.core.logging import get_logger
from app.models.file import File
from app.models.query import Query
from app.models.repository import Repository
from app.rag.llm_client import LLMClient
from app.rag.prompt_builder import PromptBuilder
from app.retrieval.hybrid_search import HybridSearchService
from app.retrieval.reranker import Reranker
from app.schemas.chat import ChatResponse, SourceCitation

logger = get_logger(__name__)


def sanitize_mermaid_diagram(raw_text: Optional[str]) -> Optional[str]:
    """Sanitize and validate a Mermaid diagram extracted from LLM markdown.

    Ensures safe node IDs, valid flowchart syntax, quoted labels,
    and removes markdown code fence artifacts.
    """
    if not raw_text or not raw_text.strip():
        return None

    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:mermaid)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    if not cleaned:
        return None

    lines = [line.rstrip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return None

    # Check header
    first_line = lines[0].strip()
    valid_headers = ("flowchart", "graph", "sequencediagram", "classdiagram", "statediagram", "erdiagram")
    if not any(first_line.lower().startswith(h) for h in valid_headers):
        lines.insert(0, "flowchart LR")
    elif first_line.lower().startswith("graph td") or first_line.lower().startswith("flowchart td"):
        lines[0] = "flowchart LR"

    sanitized_lines = [lines[0]]
    for line in lines[1:]:
        l_str = line.strip()
        if not l_str or l_str.startswith("%%"):
            continue

        # Quote unquoted square bracket labels: Node[Label (extra)] -> Node["Label (extra)"]
        l_str = re.sub(
            r'([A-Za-z0-9_]+)\[([^"\'\[\]]+)\]',
            r'\1["\2"]',
            l_str,
        )

        # Fix invalid node IDs (e.g. slashes or hyphens in node ID)
        def fix_node_id(match):
            prefix = match.group(1)
            bad_id = match.group(2)
            rest = match.group(3)
            clean_id = re.sub(r'[^A-Za-z0-9_]', '_', bad_id)
            return f"{prefix}{clean_id}{rest}"

        l_str = re.sub(r'(^|\s|-->|---|==>)([A-Za-z0-9_\-\.\/]+)(\[|\(|\{)', fix_node_id, l_str)
        sanitized_lines.append(l_str)

    if len(sanitized_lines) <= 1:
        return None

    return "\n".join(sanitized_lines)


class RAGPipeline:
    """Coordinates hybrid retrieval, reranking, citation resolution, and LLM answer generation."""

    def __init__(
        self,
        hybrid_search: Optional[HybridSearchService] = None,
        reranker: Optional[Reranker] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.hybrid_search = hybrid_search or HybridSearchService()
        self.reranker = reranker or Reranker()
        self.llm_client = llm_client or LLMClient()

    async def run(
        self,
        repo_id: str,
        question: str,
        db: AsyncSession,
        mode: str = "chat",
        top_k: int = 10,
        include_sources: bool = True,
    ) -> ChatResponse:
        """Run the end-to-end RAG pipeline for a repository."""
        start_time = time.time()
        repo_uuid = uuid.UUID(str(repo_id))

        # 1. Fetch Repository details
        repo = await db.get(Repository, repo_uuid)
        if not repo:
            raise ValueError(f"Repository {repo_id} not found.")

        repo_name = f"{repo.owner}/{repo.name}"

        # 2. Retrieve candidate chunks via Hybrid Retrieval
        search_query = question
        if mode == "architecture" and (not question.strip() or any(k in question.lower() for k in ["architecture", "diagram", "breakdown", "flowchart"])):
            search_query = "main application architecture server client entrypoint routes models pipeline database config"

        raw_results = await self.hybrid_search.search(
            query=search_query,
            repo_id=str(repo_id),
            db=db,
            top_k=top_k * 2,
        )

        # 3. Rerank using code-aware structural scoring
        reranked = self.reranker.rerank(
            query=question,
            results=raw_results,
            top_k=top_k,
        )

        # 4. Resolve source citations
        citations: List[SourceCitation] = []
        if include_sources and reranked:
            citations = await CitationResolver.resolve_citations(reranked, db=db)

        # 5. Build prompt tailored to the requested mode
        context_chunks: List[Dict[str, Any]] = [
            {
                "file_path": r.file_path,
                "start_line": r.start_line,
                "end_line": r.end_line,
                "language": r.language,
                "content": r.content,
            }
            for r in reranked
        ]

        # Fetch repository file list to ground answers with real repository structure
        file_rows = (
            await db.execute(
                select(File.path).where(File.repo_id == repo_uuid).order_by(File.path)
            )
        ).scalars().all()
        repo_files = list(file_rows)

        if mode == "summary":
            system_prompt, user_prompt = PromptBuilder.build_summary_prompt(
                repo_name=repo_name,
                file_list=repo_files,
                language_stats=repo.language_stats or {},
                sample_chunks=context_chunks,
            )
        elif mode == "api_discovery":
            system_prompt, user_prompt = PromptBuilder.build_api_discovery_prompt(
                repo_name=repo_name,
                context_chunks=context_chunks,
            )
        elif mode == "readme":
            system_prompt, user_prompt = PromptBuilder.build_readme_prompt(
                repo_name=repo_name,
                context_chunks=context_chunks,
                language_stats=repo.language_stats or {},
            )
        elif mode == "bug_scan":
            system_prompt, user_prompt = PromptBuilder.build_bug_scan_prompt(
                repo_name=repo_name,
                context_chunks=context_chunks,
            )
        elif mode == "architecture":
            system_prompt, user_prompt = PromptBuilder.build_architecture_prompt(
                repo_name=repo_name,
                context_chunks=context_chunks,
                file_list=repo_files,
                language_stats=repo.language_stats or {},
            )
        else:
            system_prompt, user_prompt = PromptBuilder.build_chat_prompt(
                question=question,
                context_chunks=context_chunks,
                repo_name=repo_name,
                file_list=repo_files,
            )

        # 6. Call LLM
        llm_response = await self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        # 7. Extract optional Mermaid diagram from response (for architecture/summary or explicit diagram requests)
        mermaid_match = re.search(r"```mermaid\n([\s\S]*?)\n```", llm_response.content)
        mermaid_diagram = None
        if mermaid_match:
            is_diagram_wanted = mode in ("architecture", "summary") or any(
                k in question.lower() for k in ["diagram", "flowchart", "architecture", "mermaid", "graph"]
            )
            if is_diagram_wanted:
                mermaid_diagram = sanitize_mermaid_diagram(mermaid_match.group(1))

        # 8. Save query record to DB
        sources_payload = [c.model_dump(mode="json") for c in citations]
        query_record = Query(
            repo_id=repo_uuid,
            user_question=question,
            response_text=llm_response.content,
            sources=sources_payload,
            mode=mode,
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used,
            processing_time_ms=elapsed_ms,
        )
        db.add(query_record)
        await db.commit()
        await db.refresh(query_record)

        return ChatResponse(
            answer=llm_response.content,
            sources=citations,
            mode=mode,
            query_id=query_record.id,
            model_used=llm_response.model,
            processing_time_ms=elapsed_ms,
            mermaid_diagram=mermaid_diagram,
        )


# Exported top-level function for route compatibility
async def run_rag_pipeline(
    repo_id: str,
    question: str,
    mode: str = "chat",
    top_k: int = 10,
    include_sources: bool = True,
    db: Optional[AsyncSession] = None,
) -> ChatResponse:
    """Helper invoked by chat routes."""
    if db is None:
        raise ValueError("Database session required for RAG pipeline.")
    pipeline = RAGPipeline()
    return await pipeline.run(
        repo_id=repo_id,
        question=question,
        db=db,
        mode=mode,
        top_k=top_k,
        include_sources=include_sources,
    )

