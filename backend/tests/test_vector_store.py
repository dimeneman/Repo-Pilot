"""Unit tests for Qdrant client creation and vector store behavior."""
import pytest
from unittest.mock import patch, MagicMock
from app.retrieval.vector_store import create_qdrant_client, VectorStoreService
from app.core.config import settings


def test_create_qdrant_client_local_default():
    """Verify local configuration uses host/port without api_key."""
    with patch("qdrant_client.QdrantClient") as mock_client:
        create_qdrant_client(host="localhost", port=6333, api_key=None, timeout=3.0)
        mock_client.assert_called_once_with(
            host="localhost",
            port=6333,
            api_key=None,
            timeout=3.0,
        )


def test_create_qdrant_client_empty_api_key_normalized():
    """Verify empty string or whitespace api_key is normalized to None."""
    with patch("qdrant_client.QdrantClient") as mock_client:
        create_qdrant_client(host="localhost", port=6333, api_key="   ", timeout=5.0)
        mock_client.assert_called_once_with(
            host="localhost",
            port=6333,
            api_key=None,
            timeout=5.0,
        )


def test_create_qdrant_client_cloud_url():
    """Verify full https URL is passed via url parameter."""
    cloud_url = "https://cluster-id.eu-central.aws.cloud.qdrant.io:6333"
    with patch("qdrant_client.QdrantClient") as mock_client:
        create_qdrant_client(host=cloud_url, api_key="test-secret-key", timeout=5.0)
        mock_client.assert_called_once_with(
            url=cloud_url,
            api_key="test-secret-key",
            timeout=5.0,
        )


def test_create_qdrant_client_cloud_host_with_api_key():
    """Verify cloud hostname without protocol is passed via host and port with api_key."""
    cloud_host = "cluster-id.eu-central.aws.cloud.qdrant.io"
    with patch("qdrant_client.QdrantClient") as mock_client:
        create_qdrant_client(host=cloud_host, port=6333, api_key="test-secret-key", timeout=5.0)
        mock_client.assert_called_once_with(
            host=cloud_host,
            port=6333,
            api_key="test-secret-key",
            timeout=5.0,
        )


@pytest.mark.asyncio
async def test_vector_store_in_memory_fallback():
    """Verify vector store safely operates in memory fallback mode when Qdrant is unreachable."""
    # Pass unreachable port to trigger fallback
    vs = VectorStoreService(host="127.0.0.1", port=59999)
    assert vs._is_memory is True
    assert vs._client is None

    # Upsert test
    chunks = [
        {
            "chunk_id": "c1",
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "content": "def test(): pass",
        }
    ]
    embeddings = [[0.1] * settings.EMBEDDING_DIMENSION]
    await vs.upsert_embeddings(chunks, embeddings, repo_id="repo-123")

    # Search test
    results = await vs.search(
        query_embedding=[0.1] * settings.EMBEDDING_DIMENSION,
        repo_id="repo-123",
        top_k=5,
    )
    assert len(results) == 1
    assert results[0].file_path == "test.py"
    assert results[0].content == "def test(): pass"
