"""
Hybrid search service — combines dense semantic vector search with BM25 keyword search.

Uses Reciprocal Rank Fusion (RRF) to merge candidate lists into a single ranked output.
"""
from __future__ import annotations

import re
import uuid
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.file import File
from app.retrieval.embedding_service import EmbeddingService
from app.retrieval.vector_store import SearchResult, VectorStoreService

logger = get_logger(__name__)


class HybridSearchService:
    """Executes hybrid (dense + sparse BM25) retrieval over repository chunks."""

    def __init__(
        self,
        vector_store: Optional[VectorStoreService] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.vector_store = vector_store or VectorStoreService()
        self.embedding_service = embedding_service or EmbeddingService()

    async def search(
        self,
        query: str,
        repo_id: str,
        db: AsyncSession,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """Perform hybrid retrieval:
        1. Dense semantic search via Vector Store
        2. Sparse BM25 / token search over stored chunks in Database
        3. Merge rankings using Reciprocal Rank Fusion (RRF)
        """
        # 1. Semantic search
        query_embedding = self.embedding_service.encode_query(query)
        semantic_results = await self.vector_store.search(
            query_embedding=query_embedding,
            repo_id=repo_id,
            top_k=top_k * 2,
        )

        # 2. Sparse / Keyword search over DB chunks
        keyword_results = await self._bm25_search(query, repo_id, db, top_k=top_k * 2)

        # If only one source returned results, return that
        if not semantic_results and not keyword_results:
            return []
        if not semantic_results:
            return keyword_results[:top_k]
        if not keyword_results:
            return semantic_results[:top_k]

        # 3. Reciprocal Rank Fusion
        fused = self.reciprocal_rank_fusion(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            k=60,
        )
        return fused[:top_k]

    async def _bm25_search(
        self,
        query: str,
        repo_id: str,
        db: AsyncSession,
        top_k: int = 20,
    ) -> List[SearchResult]:
        """Execute BM25 keyword search using rank_bm25 or token matching."""
        try:
            # Fetch chunks for this repo from DB
            try:
                repo_uuid = uuid.UUID(str(repo_id))
            except (ValueError, TypeError):
                repo_uuid = repo_id

            stmt = (
                select(Chunk, File.path, File.language)
                .join(File, Chunk.file_id == File.id)
                .where(Chunk.repo_id == repo_uuid)
                .limit(500)  # cap for fast interactive response
            )
            rows = (await db.execute(stmt)).all()
            if not rows:
                return []

            chunk_docs = []
            results_pool = []
            for chunk, file_path, language in rows:
                tokens = [t.lower() for t in re.findall(r"\w+", chunk.content)]
                chunk_docs.append(tokens)
                results_pool.append((chunk, file_path, language))

            query_tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
            if not query_tokens:
                return []

            # Try using rank_bm25 if available
            try:
                from rank_bm25 import BM25Okapi

                bm25 = BM25Okapi(chunk_docs)
                scores = bm25.get_scores(query_tokens)
            except Exception:
                # Simple TF-IDF like fallback
                scores = []
                for tokens in chunk_docs:
                    token_set = set(tokens)
                    score = sum(1.0 for q in query_tokens if q in token_set)
                    scores.append(score)

            scored_items = []
            for score, (chunk, file_path, language) in zip(scores, results_pool):
                if score > 0:
                    scored_items.append((score, chunk, file_path, language))

            scored_items.sort(key=lambda x: x[0], reverse=True)

            bm25_results: List[SearchResult] = []
            for score, chunk, file_path, language in scored_items[:top_k]:
                bm25_results.append(
                    SearchResult(
                        chunk_id=str(chunk.id),
                        score=float(score),
                        file_path=file_path,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        language=language,
                        chunk_type=chunk.chunk_type,
                    )
                )
            return bm25_results
        except Exception as exc:
            logger.error(f"BM25 search error: {exc}")
            return []

    @staticmethod
    def reciprocal_rank_fusion(
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        k: int = 60,
    ) -> List[SearchResult]:
        """Combine two ranked lists using RRF: score = sum(1 / (k + rank_i))."""
        rrf_scores: Dict[str, float] = {}
        item_map: Dict[str, SearchResult] = {}

        for rank, item in enumerate(semantic_results, start=1):
            key = f"{item.file_path}:{item.start_line}"
            item_map[key] = item
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (k + rank))

        for rank, item in enumerate(keyword_results, start=1):
            key = f"{item.file_path}:{item.start_line}"
            if key not in item_map:
                item_map[key] = item
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (k + rank))

        ranked_keys = sorted(rrf_scores.keys(), key=lambda k_val: rrf_scores[k_val], reverse=True)
        fused_results: List[SearchResult] = []
        for key in ranked_keys:
            res = item_map[key]
            res.score = round(rrf_scores[key], 5)
            fused_results.append(res)

        return fused_results

