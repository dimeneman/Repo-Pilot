"""API endpoints tests."""
import pytest
from httpx import AsyncClient
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Verify health endpoint responds with 200 OK."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "healthy"]
    assert "version" in data


@pytest.mark.asyncio
async def test_list_repositories(async_client: AsyncClient, sample_repo: Repository):
    """Verify listing repositories returns seeded records."""
    response = await async_client.get("/api/v1/repos")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(r["name"] == "test-repo" for r in data["repositories"])


@pytest.mark.asyncio
async def test_get_repository_status(async_client: AsyncClient, sample_repo: Repository):
    """Verify fetching status of a repository."""
    response = await async_client.get(f"/api/v1/repos/{sample_repo.id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["file_count"] == 2


@pytest.mark.asyncio
async def test_get_repository_files(async_client: AsyncClient, sample_repo: Repository):
    """Verify files listing for a repository."""
    response = await async_client.get(f"/api/v1/repos/{sample_repo.id}/files")
    assert response.status_code == 200
    files = response.json()
    assert len(files) == 1
    assert files[0]["path"] == "src/auth.py"


@pytest.mark.asyncio
async def test_chat_endpoint(async_client: AsyncClient, sample_repo: Repository):
    """Verify asking questions via the RAG chat endpoint."""
    payload = {
        "repo_id": str(sample_repo.id),
        "question": "Where is authentication handled?",
        "mode": "chat",
        "include_sources": True,
    }
    response = await async_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert isinstance(data["sources"], list)


@pytest.mark.asyncio
async def test_github_auth_url_endpoint(async_client: AsyncClient):
    """Verify GitHub auth URL endpoint response format."""
    response = await async_client.get("/api/v1/auth/github/url")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    if data["configured"]:
        assert "github.com/login/oauth/authorize" in data["url"]
    else:
        assert data["url"] is None


@pytest.mark.asyncio
async def test_github_user_repos_unauthorized(async_client: AsyncClient):
    """Verify GitHub repos endpoint rejects missing or invalid token."""
    response = await async_client.get("/api/v1/auth/github/repos")
    assert response.status_code == 401


def test_sanitize_mermaid_diagram():
    """Verify sanitization of raw mermaid diagrams."""
    from app.rag.pipeline import sanitize_mermaid_diagram

    # Empty / none
    assert sanitize_mermaid_diagram(None) is None
    assert sanitize_mermaid_diagram("") is None

    # Adds missing header and standardizes to flowchart LR
    raw = "```mermaid\ngraph TD\nA[Client (Browser)] --> B[API]\n```"
    sanitized = sanitize_mermaid_diagram(raw)
    assert sanitized is not None
    assert "flowchart LR" in sanitized
    assert 'A["Client (Browser)"]' in sanitized

    # Fixes bad node IDs with slashes
    raw2 = "src/main.py[Main] --> db/models.py[Models]"
    sanitized2 = sanitize_mermaid_diagram(raw2)
    assert sanitized2 is not None
    assert "/" not in sanitized2.splitlines()[1].split("[")[0]



