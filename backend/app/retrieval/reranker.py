"""
Reranking engine for code search results.

Applies domain-specific heuristics for source code:
- Function/class definition matching
- Filename and path term matches
- Exact phrase matches
- Keyword coverage
- Diversity reranking (caps chunks per file to prevent single-file domination)
"""
from __future__ import annotations

import re
from typing import Dict, List, Set

from app.core.logging import get_logger
from app.retrieval.vector_store import SearchResult

logger = get_logger(__name__)

# Conversational/question words that shouldn't match source code tokens
STOP_WORDS: Set[str] = {
    "can", "you", "list", "all", "the", "that", "are", "this", "what",
    "where", "how", "when", "why", "which", "does", "will", "with",
    "from", "have", "been", "would", "could", "should", "tell", "give",
    "show", "please", "about", "there", "their", "they", "them", "name",
    "names", "here", "into", "some", "more", "like", "just", "want", "for",
}

# Generic repository/container terms that describe the project container rather than code identifiers
META_TERMS: Set[str] = {
    "repo", "repository", "codebase", "project", "file", "files",
    "folder", "directory", "dir", "code", "script", "scripts", "module", "modules",
}


class Reranker:
    """Reranks candidate chunks using code-aware structural signals and diversity filtering."""

    @staticmethod
    def rerank(
        query: str,
        results: List[SearchResult],
        top_k: int = 5,
        max_chunks_per_file: int = 2,
    ) -> List[SearchResult]:
        """Rerank candidate results by combining vector score with structural code signals,
        ensuring diversity across files so no single file monopolizes the results.

        Args:
            query: The user's question or search term.
            results: Initial search results from vector or hybrid search.
            top_k: Number of reranked results to return.
            max_chunks_per_file: Maximum chunks allowed from the same file in the top results.

        Returns:
            Reranked and deduplicated list of SearchResults.
        """
        if not results:
            return []

        all_tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        meaningful_terms = [t for t in all_tokens if t not in STOP_WORDS]
        # Active code terms exclude general meta-words like "repo" to prevent "in this repo" matching repository.py
        code_terms = [t for t in meaningful_terms if t not in META_TERMS]
        active_terms = code_terms if code_terms else meaningful_terms

        if not active_terms:
            return results[:top_k]

        scored: List[tuple[float, SearchResult]] = []

        for item in results:
            content_lower = item.content.lower()
            path_lower = item.file_path.lower()
            bonus = 0.0

            # 1. Filename / path match (high signal: e.g. "auth" query matching "auth_service.py")
            # Only match meaningful code terms, not container terms like "repo" or "file"
            for term in code_terms:
                if re.search(rf"(?:^|[_\-/]){re.escape(term)}", path_lower):
                    bonus += 0.25
                    break

            # 2. Exact definition matches (functions, classes, routes)
            for term in code_terms:
                patterns = [
                    rf"(def|class|fn|func|function|interface|type)\s+\w*{term}\w*",
                    rf"(@(app|router)\.(get|post|put|delete|patch)\([\"'].*{term}.*[\"'])",
                    rf"(export\s+(const|function|class)\s+\w*{term}\w*)",
                ]
                matched_def = False
                for p in patterns:
                    if re.search(p, item.content, re.IGNORECASE):
                        bonus += 0.35
                        matched_def = True
                        break
                if matched_def:
                    break

            # 3. Exact query phrase match
            if len(query.strip()) > 5 and query.lower() in content_lower:
                bonus += 0.30

            # 4. Term coverage ratio over active terms
            matched_terms = sum(1 for term in active_terms if term in content_lower)
            coverage = matched_terms / len(active_terms) if active_terms else 0
            bonus += 0.20 * coverage

            # Combined score: 60% semantic + 40% lexical/structural bonus
            final_score = (0.6 * item.score) + (0.4 * min(bonus, 1.0))
            scored.append((final_score, item))

        scored.sort(key=lambda x: x[0], reverse=True)

        # 5. Diversity pass: ensure chunks come from diverse files
        reranked_results: List[SearchResult] = []
        file_counts: Dict[str, int] = {}
        deferred: List[SearchResult] = []

        for new_score, item in scored:
            item.score = round(new_score, 4)
            count = file_counts.get(item.file_path, 0)
            if count < max_chunks_per_file:
                reranked_results.append(item)
                file_counts[item.file_path] = count + 1
                if len(reranked_results) >= top_k:
                    break
            else:
                deferred.append(item)

        # Backfill if not enough distinct files exist to reach top_k
        if len(reranked_results) < top_k and deferred:
            for item in deferred:
                reranked_results.append(item)
                if len(reranked_results) >= top_k:
                    break

        return reranked_results

