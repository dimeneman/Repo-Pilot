"""
Security utilities for RepoPilot.

Provides JWT token creation / verification, password hashing, and optional
GitHub OAuth helpers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger()

# ── Password hashing ────────────────────────────────────────────────────
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        plain: The plain-text password to hash.

    Returns:
        The bcrypt hash string.
    """
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify *plain* against a bcrypt *hashed* value.

    Args:
        plain: The plain-text password.
        hashed: The stored bcrypt hash.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.
    """
    return _pwd_ctx.verify(plain, hashed)


# ── JWT tokens ───────────────────────────────────────────────────────────

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        data: Payload claims to embed in the token.
        expires_delta: Optional custom expiry duration.  Defaults to
            ``settings.ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns:
        The encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def verify_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT token.

    Args:
        token: The raw JWT string.

    Returns:
        The decoded payload dictionary, or ``None`` if the token is
        invalid or expired.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError as exc:
        log.warning(f"JWT verification failed: {exc}")
        return None


# ── GitHub OAuth helpers ─────────────────────────────────────────────────

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_API = "https://api.github.com/user"
GITHUB_REPOS_API = "https://api.github.com/user/repos"


def build_github_authorize_url(redirect_uri: str, state: str) -> str:
    """Build the GitHub OAuth authorization redirect URL.

    Args:
        redirect_uri: The callback URL GitHub should redirect to.
        state: An opaque CSRF-protection value.

    Returns:
        A fully-qualified GitHub authorization URL.
    """
    from urllib.parse import urlencode

    client_id = (settings.GITHUB_CLIENT_ID or "").strip()
    params = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "read:user user:email repo",
        "state": state,
    })
    return f"{GITHUB_AUTH_URL}?{params}"


async def exchange_github_code(
    code: str,
    redirect_uri: str | None = None,
) -> dict[str, Any] | None:
    """Exchange an OAuth authorization code for an access token.

    Args:
        code: The one-time authorization code from GitHub.
        redirect_uri: Optional redirect URI used during the authorize step.

    Returns:
        Parsed JSON response with ``access_token``, or error dict / None on error.
    """
    import httpx  # imported lazily to keep module-level imports light

    client_id = (settings.GITHUB_CLIENT_ID or "").strip()
    client_secret = (settings.GITHUB_CLIENT_SECRET or "").strip()

    payload: dict[str, Any] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code.strip(),
    }
    if redirect_uri:
        payload["redirect_uri"] = redirect_uri.strip()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_TOKEN_URL,
            data=payload,
            headers={
                "Accept": "application/json",
                "User-Agent": "RepoPilot/1.0",
            },
        )
        if resp.status_code != 200:
            log.error(f"GitHub token exchange failed (HTTP {resp.status_code}): {resp.text}")
            return None
        data: dict[str, Any] = resp.json()
        if "access_token" not in data:
            log.error(f"GitHub token exchange response: {data}")
            return data
        return data


async def get_github_user(access_token: str) -> dict[str, Any] | None:
    """Fetch the authenticated user's profile from GitHub.

    Args:
        access_token: A valid GitHub personal / OAuth access token.

    Returns:
        Parsed JSON user object, or ``None`` on failure.
    """
    import httpx

    clean_token = access_token.strip()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GITHUB_USER_API,
            headers={
                "Authorization": f"Bearer {clean_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "RepoPilot/1.0",
            },
        )
        if resp.status_code != 200:
            log.error(f"GitHub user fetch failed (HTTP {resp.status_code}): {resp.text}")
            return None
        return resp.json()


async def get_github_user_repos(access_token: str) -> list[dict[str, Any]] | None:
    """Fetch repositories accessible by the authenticated user from GitHub.

    Args:
        access_token: A valid GitHub personal / OAuth access token.

    Returns:
        List of repository dicts, or ``None`` on failure.
    """
    import httpx

    clean_token = access_token.strip()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_REPOS_API}?per_page=100&sort=updated&affiliation=owner,collaborator,organization_member",
            headers={
                "Authorization": f"Bearer {clean_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "RepoPilot/1.0",
            },
        )
        if resp.status_code != 200:
            log.error(f"GitHub user repos fetch failed (HTTP {resp.status_code}): {resp.text}")
            return None
        return resp.json()
