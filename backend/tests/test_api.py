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


@pytest.mark.asyncio
async def test_patch_job_status(async_client: AsyncClient, sample_repo: Repository):
    """Verify external runners can update job progress via PATCH /api/v1/jobs/{id}."""
    # First create a job via reindex
    reindex_resp = await async_client.post(f"/api/v1/repos/{sample_repo.id}/reindex")
    job_id = reindex_resp.json()["job_id"]

    # External runner reports cloning stage
    patch_payload = {
        "status": "running",
        "stage": "cloning",
        "progress": 0.25,
        "step_description": "Cloning repository in GitHub Actions",
    }
    patch_resp = await async_client.patch(f"/api/v1/jobs/{job_id}", json=patch_payload)
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["status"] == "running"
    assert patch_data["stage"] == "cloning"
    assert patch_data["progress"] == 0.25
    assert patch_data["step_description"] == "Cloning repository in GitHub Actions"

    # External runner reports completed
    complete_payload = {
        "status": "completed",
        "stage": "done",
        "progress": 1.0,
        "step_description": "Indexed successfully in runner",
    }
    complete_resp = await async_client.patch(f"/api/v1/jobs/{job_id}", json=complete_payload)
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"

    # Verify repository status became ready
    status_resp = await async_client.get(f"/api/v1/repos/{sample_repo.id}/status")
    assert status_resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_github_actions_service_dispatch(monkeypatch):
    """Verify GitHub Actions repository_dispatch call with proper headers and payload."""
    import httpx
    from app.services.github_actions import GitHubActionsService

    service = GitHubActionsService(
        token="ghp_testtoken123",
        owner="dimeneman",
        repo="Repo-Pilot",
        event_type="ingest_repo",
    )
    assert service.is_configured is True

    captured_request = {}

    async def mock_post(self, url, headers=None, json=None):
        captured_request["url"] = url
        captured_request["headers"] = headers
        captured_request["json"] = json
        return httpx.Response(status_code=204)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    success = await service.dispatch_ingest_job(
        job_id="test-job-id",
        repo_id="test-repo-id",
        repo_url="https://github.com/octocat/Hello-World",
        branch="main",
    )
    assert success is True
    assert "https://api.github.com/repos/dimeneman/Repo-Pilot/dispatches" in captured_request["url"]
    assert captured_request["headers"]["Authorization"] == "Bearer ghp_testtoken123"
    assert captured_request["json"]["event_type"] == "ingest_repo"
    assert captured_request["json"]["client_payload"]["job_id"] == "test-job-id"


@pytest.mark.asyncio
async def test_github_actions_service_error_handling(monkeypatch):
    """Verify GitHub Actions dispatch raises RuntimeError on non-204 responses."""
    import httpx
    from app.services.github_actions import GitHubActionsService

    service = GitHubActionsService(
        token="ghp_invalid",
        owner="dimeneman",
        repo="Repo-Pilot",
    )

    async def mock_post_err(self, url, headers=None, json=None):
        return httpx.Response(status_code=401, text='{"message":"Bad credentials"}')

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post_err)

    with pytest.raises(RuntimeError) as exc_info:
        await service.dispatch_ingest_job(
            job_id="test-job-id",
            repo_id="test-repo-id",
            repo_url="https://github.com/octocat/Hello-World",
        )
    assert "401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dispatch_ingestion_job_routing(monkeypatch):
    """Verify dispatch_ingestion_job falls back to local queue when token is absent."""
    from app.services.ingestion import dispatch_ingestion_job
    from app.core.config import settings

    # In local/auto mode without GITHUB_ACTIONS_TOKEN
    monkeypatch.setattr(settings, "GITHUB_ACTIONS_TOKEN", None)
    monkeypatch.setattr(settings, "INGESTION_RUNNER", "auto")

    runner = await dispatch_ingestion_job(
        job_id="job-123",
        repo_id="repo-123",
        repo_url="https://github.com/test/repo",
    )
    assert runner == "local"

    # When GITHUB_ACTIONS_TOKEN is present
    monkeypatch.setattr(settings, "GITHUB_ACTIONS_TOKEN", "ghp_valid")
    import httpx
    async def mock_ok_post(self, url, headers=None, json=None):
        return httpx.Response(status_code=204)
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_ok_post)

    runner2 = await dispatch_ingestion_job(
        job_id="job-456",
        repo_id="repo-456",
        repo_url="https://github.com/test/repo",
    )
    assert runner2 == "github_actions"


@pytest.mark.asyncio
async def test_worker_execute_fail_job(async_client: AsyncClient, sample_repo: Repository, db_session):
    """Verify execute_fail_job records failure in database."""
    from app.worker import execute_fail_job
    # Create job
    reindex_resp = await async_client.post(f"/api/v1/repos/{sample_repo.id}/reindex")
    job_id = reindex_resp.json()["job_id"]

    # Call execute_fail_job with test db session
    await execute_fail_job(job_id, "Runner timed out or crashed", db_session=db_session)

    # Check status
    job_resp = await async_client.get(f"/api/v1/jobs/{job_id}")
    job_data = job_resp.json()
    assert job_data["status"] == "failed"
    assert job_data["stage"] == "failed"
    assert "Runner timed out" in job_data["error_message"]

    repo_resp = await async_client.get(f"/api/v1/repos/{sample_repo.id}/status")
    assert repo_resp.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_reingest_existing_repo_creates_new_job(async_client: AsyncClient, sample_repo: Repository):
    """Verify that posting an existing repository URL triggers clean re-indexing without manual job id."""
    payload = {
        "url": sample_repo.url,
    }
    response = await async_client.post("/api/v1/repos/ingest", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["id"] == str(sample_repo.id)
    assert "job_id" in data
    assert data["job_id"] is not None

    job_id = data["job_id"]
    job_resp = await async_client.get(f"/api/v1/jobs/{job_id}")
    assert job_resp.status_code == 200
    job_data = job_resp.json()
    assert job_data["status"] == "pending"
    assert job_data["job_type"] == "reindex"


@pytest.mark.asyncio
async def test_dispatch_direct_runner_mode(monkeypatch):
    """Verify INGESTION_RUNNER=direct routes to in-process execution."""
    from app.services.ingestion import dispatch_ingestion_job
    from app.core.config import settings

    monkeypatch.setattr(settings, "INGESTION_RUNNER", "direct")
    runner = await dispatch_ingestion_job(
        job_id="job-direct",
        repo_id="repo-direct",
        repo_url="https://github.com/test/repo",
    )
    assert runner == "direct"







