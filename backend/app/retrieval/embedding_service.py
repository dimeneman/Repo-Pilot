"""
Embedding service — generates dense vector embeddings for code and queries.

Uses sentence-transformers (all-MiniLM-L6-v2) by default, with lazy loading
and caching.
"""
from __future__ import annotations

import hashlib
import math
from typing import List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Singleton service for generating vector embeddings."""

    _instance: Optional[EmbeddingService] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: Optional[str] = None):
        if self._initialized:
            return
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self._model = None
        self._initialized = True

    def _load_model(self):
        """Lazy load the sentence transformer model."""
        if self._model is not None:
            return self._model

        if self.model_name == "fallback":
            self._model = "fallback"
            return self._model

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self.model_name}")
            try:
                self._model = SentenceTransformer(self.model_name, local_files_only=True)
            except Exception:
                self._model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully.")
            return self._model

        except Exception as exc:
            logger.warning(
                f"Could not load sentence_transformers ({exc}). "
                "Using deterministic fallback embeddings."
            )
            self._model = "fallback"
            return self._model

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Batch encode a list of texts into dense vectors.

        Args:
            texts: List of strings to encode.

        Returns:
            List of embedding vectors (float lists).
        """
        if not texts:
            return []

        model = self._load_model()
        if model != "fallback":
            try:
                embeddings = model.encode(
                    texts,
                    batch_size=32,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )
                return [emb.tolist() for emb in embeddings]
            except Exception as exc:
                logger.error(f"Encoding failed: {exc}. Using fallback.")

        # Fallback deterministic embeddings for testing or offline environments
        return [self._fallback_encode(t) for t in texts]

    def encode_query(self, query: str) -> List[float]:
        """Encode a single query string.

        Args:
            query: The user's search query.

        Returns:
            Vector embedding as a list of floats.
        """
        return self.encode([query])[0]

    def _fallback_encode(self, text: str) -> List[float]:
        """Produce a deterministic, normalized vector based on MD5 and word hashes."""
        vec = [0.0] * self.dimension
        words = text.lower().split()
        for idx, word in enumerate(words):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            pos = h % self.dimension
            vec[pos] += 1.0 / (idx + 1)

        # Normalize vector
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

