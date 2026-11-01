"""
Vector store service — wraps Qdrant with an in-memory fallback for development and testing.

Provides indexing, similarity search filtered by repository, deletion, and collection management.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Standardized vector search result."""

    chunk_id: str
    score: float
    file_path: str
    start_line: int
    end_line: int
    content: str
    language: Optional[str] = None
    chunk_type: str = "code"
    metadata: Optional[Dict[str, Any]] = None


def create_qdrant_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    api_key: Optional[str] = None,
    timeout: float = 5.0,
):
    """Create a configured QdrantClient instance supporting local and cloud deployments.

    - If host starts with 'http://' or 'https://', it is passed as `url`.
    - If `api_key` is provided (or configured via settings.QDRANT_API_KEY), it is passed to authenticate.
    - Otherwise, standard local host and port are used.
    """
    from qdrant_client import QdrantClient

    target_host = host or settings.QDRANT_HOST
    target_port = port or settings.QDRANT_PORT
    raw_key = api_key if api_key is not None else settings.QDRANT_API_KEY
    target_api_key = raw_key.strip() if raw_key and raw_key.strip() else None

    if target_host.startswith("http://") or target_host.startswith("https://"):
        return QdrantClient(
            url=target_host,
            api_key=target_api_key,
            timeout=timeout,
        )
    return QdrantClient(
        host=target_host,
        port=target_port,
        api_key=target_api_key,
        timeout=timeout,
    )


class VectorStoreService:
    """Manages vector storage and similarity search in Qdrant (or in-memory fallback)."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        self.collection = collection or settings.QDRANT_COLLECTION
        raw_key = api_key if api_key is not None else settings.QDRANT_API_KEY
        self.api_key = raw_key.strip() if raw_key and raw_key.strip() else None
        self._client = None
        self._is_memory = False
        self._memory_store: Dict[str, List[Dict[str, Any]]] = {}  # repo_id -> list of chunk dicts
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Qdrant or fallback to memory."""
        endpoint = (
            self.host
            if (self.host.startswith("http://") or self.host.startswith("https://"))
            else f"{self.host}:{self.port}"
        )
        try:
            client = create_qdrant_client(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
                timeout=5.0,
            )
            client.get_collections()
            self._client = client
            self._is_memory = False
            auth_info = " with API key" if self.api_key else ""
            logger.info(f"Connected to Qdrant at {endpoint}{auth_info}")
        except Exception as exc:
            logger.warning(
                f"Could not connect to Qdrant at {endpoint} ({exc}). "
                "Operating in in-memory fallback mode."
            )
            self._is_memory = True
            self._client = None

    async def ensure_collection(self, dimension: Optional[int] = None) -> None:
        """Create the target collection if it does not already exist."""
        dim = dimension or settings.EMBEDDING_DIMENSION
        if self._is_memory or not self._client:
            return

        try:
            from qdrant_client.http import models

            collections = self._client.get_collections().collections
            exists = any(c.name == self.collection for c in collections)
            if not exists:
                self._client.create_collection(
                    collection_name=self.collection,
                    vectors_config=models.VectorParams(
                        size=dim,
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection '{self.collection}' (dim={dim})")
        except Exception as exc:
            logger.error(f"Error ensuring collection '{self.collection}': {exc}")
            self._is_memory = True

    async def upsert_embeddings(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        repo_id: str,
    ) -> None:
        """Insert or replace vector embeddings and metadata for a repository's chunks.

        Args:
            chunks: List of chunk metadata dictionaries.
            embeddings: Corresponding list of vector embeddings.
            repo_id: Identifier of the repository.
        """
        if not chunks or not embeddings:
            return

        if self._is_memory or not self._client:
            if repo_id not in self._memory_store:
                self._memory_store[repo_id] = []
            for chunk, emb in zip(chunks, embeddings):
                self._memory_store[repo_id].append({
                    "chunk": chunk,
                    "embedding": emb,
                })
            return

        try:
            from qdrant_client.http import models

            points = []
            for chunk, emb in zip(chunks, embeddings):
                chunk_id = str(chunk.get("id") or uuid.uuid4())
                points.append(
                    models.PointStruct(
                        id=chunk_id,
                        vector=emb,
                        payload={
                            "repo_id": str(repo_id),
                            "chunk_id": chunk_id,
                            "file_id": str(chunk.get("file_id", "")),
                            "file_path": chunk.get("file_path", ""),
                            "start_line": chunk.get("start_line", 1),
                            "end_line": chunk.get("end_line", 1),
                            "content": chunk.get("content", ""),
                            "language": chunk.get("language", ""),
                            "chunk_type": chunk.get("chunk_type", "code"),
                            "chunk_index": chunk.get("chunk_index", 0),
                        },
                    )
                )

            # Batch upload points
            self._client.upsert(
                collection_name=self.collection,
                points=points,
                wait=True,
            )
            logger.info(f"Upserted {len(points)} vectors to Qdrant for repo {repo_id}")
        except Exception as exc:
            logger.error(f"Failed to upsert to Qdrant: {exc}. Saving in memory.")
            self._is_memory = True
            await self.upsert_embeddings(chunks, embeddings, repo_id)

    async def search(
        self,
        query_embedding: List[float],
        repo_id: str,
        top_k: int = 10,
        score_threshold: float = 0.2,
    ) -> List[SearchResult]:
        """Perform semantic similarity search for a given repository.

        Args:
            query_embedding: Dense embedding vector for the user query.
            repo_id: Repository ID to scope the search to.
            top_k: Maximum number of results.
            score_threshold: Minimum cosine similarity score.
        """
        if self._is_memory or not self._client:
            return self._memory_search(query_embedding, repo_id, top_k, score_threshold)

        try:
            from qdrant_client.http import models

            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="repo_id",
                        match=models.MatchValue(value=str(repo_id)),
                    )
                ]
            )

            if hasattr(self._client, "query_points"):
                response = self._client.query_points(
                    collection_name=self.collection,
                    query=query_embedding,
                    query_filter=query_filter,
                    limit=top_k,
                    score_threshold=score_threshold,
                )
                hits = response.points
            else:
                hits = self._client.search(
                    collection_name=self.collection,
                    query_vector=query_embedding,
                    query_filter=query_filter,
                    limit=top_k,
                    score_threshold=score_threshold,
                )

            results: List[SearchResult] = []
            for hit in hits:
                payload = hit.payload or {}
                results.append(
                    SearchResult(
                        chunk_id=str(payload.get("chunk_id", hit.id)),
                        score=float(hit.score),
                        file_path=payload.get("file_path", "unknown"),
                        start_line=int(payload.get("start_line", 1)),
                        end_line=int(payload.get("end_line", 1)),
                        content=payload.get("content", ""),
                        language=payload.get("language"),
                        chunk_type=payload.get("chunk_type", "code"),
                        metadata=payload,
                    )
                )
            return results
        except Exception as exc:
            logger.error(f"Qdrant search failed: {exc}. Falling back to memory.")
            return self._memory_search(query_embedding, repo_id, top_k, score_threshold)

    def _memory_search(
        self,
        query_embedding: List[float],
        repo_id: str,
        top_k: int,
        score_threshold: float,
    ) -> List[SearchResult]:
        """In-memory cosine similarity search."""
        import math

        items = self._memory_store.get(str(repo_id), [])
        if not items:
            return []

        scored: List[tuple[float, Dict[str, Any]]] = []
        for item in items:
            vec = item["embedding"]
            # Cosine similarity
            dot = sum(a * b for a, b in zip(query_embedding, vec))
            norm_q = math.sqrt(sum(a * a for a in query_embedding)) or 1e-9
            norm_v = math.sqrt(sum(b * b for b in vec)) or 1e-9
            sim = dot / (norm_q * norm_v)
            if sim >= score_threshold:
                scored.append((sim, item["chunk"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: List[SearchResult] = []
        for score, chunk in scored[:top_k]:
            results.append(
                SearchResult(
                    chunk_id=str(chunk.get("id", uuid.uuid4())),
                    score=float(score),
                    file_path=chunk.get("file_path", "unknown"),
                    start_line=int(chunk.get("start_line", 1)),
                    end_line=int(chunk.get("end_line", 1)),
                    content=chunk.get("content", ""),
                    language=chunk.get("language"),
                    chunk_type=chunk.get("chunk_type", "code"),
                    metadata=chunk,
                )
            )
        return results

    async def delete_by_repo(self, repo_id: str) -> None:
        """Delete all vectors for a specific repository."""
        if str(repo_id) in self._memory_store:
            del self._memory_store[str(repo_id)]

        if not self._is_memory and self._client:
            try:
                from qdrant_client.http import models

                self._client.delete(
                    collection_name=self.collection,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="repo_id",
                                    match=models.MatchValue(value=str(repo_id)),
                                )
                            ]
                        )
                    ),
                )
                logger.info(f"Deleted vectors in Qdrant for repo {repo_id}")
            except Exception as exc:
                logger.error(f"Failed to delete vectors from Qdrant: {exc}")

    async def get_collection_info(self) -> Dict[str, Any]:
        """Return information about the collection status."""
        if self._is_memory or not self._client:
            total_points = sum(len(v) for v in self._memory_store.values())
            return {
                "collection": self.collection,
                "status": "memory_mode",
                "total_points": total_points,
            }
        try:
            info = self._client.get_collection(self.collection)
            return {
                "collection": self.collection,
                "status": "connected",
                "vectors_count": getattr(info, "vectors_count", 0),
                "points_count": getattr(info, "points_count", 0),
            }
        except Exception as exc:
            return {"collection": self.collection, "status": f"error: {exc}"}


# Alias for dependency injection
VectorStore = VectorStoreService

