"""VectorStore service alias for dependency injection."""
from app.retrieval.vector_store import VectorStoreService, VectorStore, create_qdrant_client

__all__ = ["VectorStoreService", "VectorStore", "create_qdrant_client"]

