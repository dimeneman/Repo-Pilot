"""
GitHub Actions workflow dispatch service for asynchronous ingestion.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GitHubActionsService:
    """Dispatches repository ingestion jobs to GitHub Actions via repository_dispatch."""

    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        event_type: Optional[str] = None,
    ):
        self.token = token or settings.GITHUB_ACTIONS_TOKEN
        self.owner = owner or settings.GITHUB_REPO_OWNER
        self.repo = repo or settings.GITHUB_REPO_NAME
        self.event_type = event_type or settings.GITHUB_WORKFLOW_EVENT_TYPE

    @property
    def is_configured(self) -> bool:
        """Return True if required GitHub Actions credentials and target repo are set."""
        return bool(self.token and self.token.strip() and self.owner and self.repo)

    async def dispatch_ingest_job(
        self,
        job_id: str,
        repo_id: str,
        repo_url: str,
        branch: Optional[str] = "main",
        access_token: Optional[str] = None,
    ) -> bool:
        """Trigger repository_dispatch in GitHub Actions for repository ingestion.

        Args:
            job_id: UUID of the pending Job.
            repo_id: UUID of the Repository.
            repo_url: Git clone URL.
            branch: Git branch name.
            access_token: Optional GitHub access token for cloning private repos.

        Returns:
            True if dispatched successfully (HTTP 204).

        Raises:
            RuntimeError: If dispatch fails and error details are returned.
        """
        if not self.is_configured:
            raise RuntimeError(
                "GitHub Actions runner is not configured. Missing GITHUB_ACTIONS_TOKEN, "
                "GITHUB_REPO_OWNER, or GITHUB_REPO_NAME."
            )

        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/dispatches"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token.strip()}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RepoPilot-Backend",
        }
        payload = {
            "event_type": self.event_type,
            "client_payload": {
                "job_id": str(job_id),
                "repo_id": str(repo_id),
                "repo_url": repo_url,
                "branch": branch or "main",
                "access_token": access_token or "",
            },
        }

        logger.info(
            f"Dispatching GitHub Actions ingestion workflow: event={self.event_type} "
            f"target={self.owner}/{self.repo} for job={job_id} repo={repo_id}"
        )

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(api_url, headers=headers, json=payload)

        if resp.status_code == 204:
            logger.info(
                f"Successfully dispatched GitHub Actions ingestion workflow for job {job_id}"
            )
            return True

        err_msg = (
            f"GitHub Actions dispatch failed (HTTP {resp.status_code}): {resp.text}"
        )
        logger.error(err_msg)
        raise RuntimeError(err_msg)

