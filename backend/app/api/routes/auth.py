"""
Authentication and GitHub Account Linking Routes.

Provides endpoints for GitHub OAuth flow, Personal Access Token validation,
user profile retrieval, and repository fetching from GitHub API.
"""
from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    build_github_authorize_url,
    exchange_github_code,
    get_github_user,
    get_github_user_repos,
)
from app.db.session import get_db
from app.models.repository import Repository

logger = get_logger(__name__)
router = APIRouter()


# ── Request / Response Schemas ───────────────────────────────────────────────

class GitHubAuthUrlResponse(BaseModel):
    configured: bool
    url: Optional[str] = None
    client_id: Optional[str] = None
    message: Optional[str] = None


class GitHubCallbackRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None


class GitHubTokenLoginRequest(BaseModel):
    token: str = Field(..., description="GitHub Personal Access Token (PAT) or OAuth token")


class GitHubUserResponse(BaseModel):
    id: int
    login: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    html_url: Optional[str] = None
    email: Optional[str] = None
    public_repos: Optional[int] = None
    bio: Optional[str] = None


class GitHubAuthResponse(BaseModel):
    access_token: str
    user: Dict[str, Any]


class GitHubRepoItem(BaseModel):
    id: int
    name: str
    full_name: str
    owner: str
    html_url: str
    clone_url: str
    description: Optional[str] = None
    private: bool
    default_branch: str
    language: Optional[str] = None
    stargazers_count: int = 0
    updated_at: Optional[str] = None
    is_indexed: bool = False
    indexed_repo_id: Optional[str] = None


class GitHubReposListResponse(BaseModel):
    repositories: List[GitHubRepoItem]
    total: int


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/github/url",
    response_model=GitHubAuthUrlResponse,
    summary="Get GitHub OAuth authorization URL",
)
async def get_github_auth_url(
    redirect_uri: str = Query("http://localhost:3000/auth/callback"),
) -> GitHubAuthUrlResponse:
    """Return the GitHub OAuth authorize redirect URL if configured."""
    client_id = settings.GITHUB_CLIENT_ID.strip() if settings.GITHUB_CLIENT_ID else ""
    if not client_id:
        return GitHubAuthUrlResponse(
            configured=False,
            url=None,
            client_id=None,
            message="GitHub OAuth credentials (GITHUB_CLIENT_ID) are not configured in your .env file. You can connect using a Personal Access Token or configure OAuth.",
        )

    state = secrets.token_hex(16)
    auth_url = build_github_authorize_url(redirect_uri=redirect_uri, state=state)
    return GitHubAuthUrlResponse(
        configured=True,
        url=auth_url,
        client_id=client_id,
    )


@router.post(
    "/github/callback",
    response_model=GitHubAuthResponse,
    summary="Exchange GitHub authorization code for token and profile",
)
async def github_oauth_callback(
    payload: GitHubCallbackRequest,
) -> GitHubAuthResponse:
    """Exchange OAuth one-time code for GitHub token and fetch user details."""
    token_data = await exchange_github_code(
        code=payload.code,
        redirect_uri=payload.redirect_uri,
    )
    if not token_data or "access_token" not in token_data:
        err_msg = "Failed to exchange GitHub authorization code. Please try signing in again."
        if token_data and "error_description" in token_data:
            err_msg = str(token_data["error_description"])
        elif token_data and "error" in token_data:
            err_msg = f"GitHub OAuth Error: {token_data['error']}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )

    access_token = token_data["access_token"]
    user_data = await get_github_user(access_token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve user profile with GitHub access token.",
        )

    return GitHubAuthResponse(
        access_token=access_token,
        user=user_data,
    )


@router.post(
    "/github/token-login",
    response_model=GitHubAuthResponse,
    summary="Connect GitHub account using Personal Access Token (PAT)",
)
async def github_token_login(
    payload: GitHubTokenLoginRequest,
) -> GitHubAuthResponse:
    """Validate a user-provided GitHub Personal Access Token and link the account."""
    clean_token = payload.token.strip()
    if not clean_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token cannot be empty.",
        )

    user_data = await get_github_user(clean_token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub access token or insufficient permissions.",
        )

    return GitHubAuthResponse(
        access_token=clean_token,
        user=user_data,
    )


@router.get(
    "/github/user",
    response_model=Dict[str, Any],
    summary="Get authenticated GitHub user profile",
)
async def get_current_github_user(
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Retrieve the current user profile using the passed Authorization Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
        )

    token = authorization.split(" ", 1)[1].strip()
    user = await get_github_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired GitHub access token.",
        )
    return user


@router.get(
    "/github/repos",
    response_model=GitHubReposListResponse,
    summary="Fetch accessible repositories from user's GitHub account",
)
async def list_user_github_repos(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> GitHubReposListResponse:
    """Fetch repositories from GitHub and annotate them with indexing status in RepoPilot."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
        )

    token = authorization.split(" ", 1)[1].strip()
    raw_repos = await get_github_user_repos(token)
    if raw_repos is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch repositories from GitHub. Check token validity and rate limits.",
        )

    # 1. Fetch currently indexed repositories in RepoPilot
    result = await db.execute(select(Repository.id, Repository.url, Repository.name, Repository.owner))
    db_repos = result.all()

    # Map indexed repos by URL and full_name (lowercase for robust match)
    indexed_map: Dict[str, str] = {}
    for r_id, r_url, r_name, r_owner in db_repos:
        if r_url:
            clean_url = r_url.rstrip("/").lower()
            indexed_map[clean_url] = str(r_id)
            if clean_url.endswith(".git"):
                indexed_map[clean_url[:-4]] = str(r_id)
            else:
                indexed_map[f"{clean_url}.git"] = str(r_id)
        if r_owner and r_name:
            indexed_map[f"{r_owner}/{r_name}".lower()] = str(r_id)

    # 2. Transform GitHub API response into structured items
    items: List[GitHubRepoItem] = []
    for r in raw_repos:
        full_name = r.get("full_name") or ""
        html_url = r.get("html_url") or ""
        clone_url = r.get("clone_url") or html_url

        # Check indexing status
        clean_html = html_url.rstrip("/").lower()
        clean_full = full_name.lower()
        indexed_id = indexed_map.get(clean_full) or indexed_map.get(clean_html)
        is_indexed = bool(indexed_id)

        owner_info = r.get("owner", {})
        owner_login = owner_info.get("login") if isinstance(owner_info, dict) else ""

        items.append(
            GitHubRepoItem(
                id=r.get("id", 0),
                name=r.get("name", ""),
                full_name=full_name,
                owner=owner_login,
                html_url=html_url,
                clone_url=clone_url,
                description=r.get("description"),
                private=bool(r.get("private", False)),
                default_branch=r.get("default_branch") or "main",
                language=r.get("language"),
                stargazers_count=r.get("stargazers_count", 0),
                updated_at=r.get("updated_at"),
                is_indexed=is_indexed,
                indexed_repo_id=indexed_id,
            )
        )

    return GitHubReposListResponse(
        repositories=items,
        total=len(items),
    )

