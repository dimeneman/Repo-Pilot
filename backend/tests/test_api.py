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


@pytest.mark.asyncio
async def test_ingest_endpoint_non_blocking_job(async_client: AsyncClient):
    """Verify POST /repos/ingest returns 202 immediately with job_id."""
    payload = {
        "url": "https://github.com/repopilot/async-test-repo",
        "branch": "main",
    }
    response = await async_client.post("/api/v1/repos/ingest", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert "job_id" in data
    assert data["job_id"] is not None

    repo_id = data["id"]
    job_id = data["job_id"]

    # Verify Job endpoint returns job status
    job_resp = await async_client.get(f"/api/v1/jobs/{job_id}")
    assert job_resp.status_code == 200
    job_data = job_resp.json()
    assert job_data["id"] == job_id
    assert job_data["repo_id"] == repo_id
    assert job_data["status"] == "pending"
    assert job_data["stage"] == "pending"

    # Verify Repo status polling endpoint reflects job progress and stage
    status_resp = await async_client.get(f"/api/v1/repos/{repo_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["id"] == repo_id
    assert status_data["job_id"] == job_id
    assert status_data["stage"] == "pending"


@pytest.mark.asyncio
async def test_job_not_found(async_client: AsyncClient):
    """Verify 404 is returned for non-existent job ID."""
    import uuid
    dummy_id = uuid.uuid4()
    response = await async_client.get(f"/api/v1/jobs/{dummy_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reindex_endpoint_creates_job(async_client: AsyncClient, sample_repo: Repository):
    """Verify POST /repos/{id}/reindex creates background job and returns 202."""
    response = await async_client.post(f"/api/v1/repos/{sample_repo.id}/reindex")
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["job_id"] is not None

    job_id = data["job_id"]
    job_resp = await async_client.get(f"/api/v1/jobs/{job_id}")
    assert job_resp.status_code == 200
    job_data = job_resp.json()
    assert job_data["job_type"] == "reindex"
    assert job_data["status"] == "pending"




