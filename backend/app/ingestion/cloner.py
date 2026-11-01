"""
Repository cloner — clones GitHub repositories via git CLI.

Handles URL parsing, shallow cloning, and cleanup on failure.
"""
from __future__ import annotations

import asyncio
import re
import shutil
from pathlib import Path
from typing import Tuple

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Regex to extract owner and repo name from various GitHub URL formats
_GITHUB_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?/?$"
)


class RepoCloner:
    """Clones GitHub repositories to the local filesystem.

    Uses shallow clones (``--depth=1``) for speed, falling back to full
    clones only if the caller explicitly requests a specific branch that
    is not the remote HEAD.
    """

    # ------------------------------------------------------------------ #
    # Public helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def parse_github_url(url: str) -> Tuple[str, str]:
        """Extract *owner* and *repo name* from a GitHub URL.

        Supports formats:
        - ``https://github.com/owner/repo``
        - ``https://github.com/owner/repo.git``
        - ``https://www.github.com/owner/repo``
        - ``github.com/owner/repo``

        Returns:
            Tuple of ``(owner, repo_name)``.

        Raises:
            ValueError: If the URL does not match any known pattern.
        """
        # Normalise – add scheme when missing so the regex matches
        normalised = url.strip()
        if not normalised.startswith(("http://", "https://")):
            normalised = f"https://{normalised}"

        match = _GITHUB_URL_PATTERN.match(normalised)
        if not match:
            raise ValueError(
                f"Invalid GitHub URL: '{url}'. "
                "Expected format: https://github.com/owner/repo"
            )
        return match.group("owner"), match.group("repo")

    # ------------------------------------------------------------------ #
    # Clone
    # ------------------------------------------------------------------ #

    async def clone_repository(
        self,
        url: str,
        branch: str | None = None,
        target_dir: str | None = None,
        access_token: str | None = None,
    ) -> Path:
        """Clone a GitHub repository to ``target_dir``.

        Args:
            url: The HTTPS GitHub URL of the repository.
            branch: Optional branch to clone.  When *None* the remote HEAD
                (usually ``main`` or ``master``) is used.
            target_dir: Destination directory.  Defaults to
                ``settings.REPOS_DIR / owner / repo``.

        Returns:
            :class:`pathlib.Path` to the cloned repository root.

        Raises:
            RuntimeError: If the ``git clone`` process fails.
            ValueError: If the URL cannot be parsed.
        """
        owner, repo_name = self.parse_github_url(url)

        if target_dir is None:
            target_path = Path(settings.REPOS_DIR) / owner / repo_name
        else:
            target_path = Path(target_dir)

        # Ensure a clean slate (idempotent)
        if target_path.exists():
            logger.info("Target directory already exists – removing: %s", target_path)
            shutil.rmtree(target_path, ignore_errors=True)

        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Normalise URL to always include https scheme
        clone_url = url.strip()
        if not clone_url.startswith(("http://", "https://")):
            clone_url = f"https://{clone_url}"
        if not clone_url.endswith(".git"):
            clone_url = f"{clone_url}.git"

        # Use authenticated URL if token provided (supports private repos)
        exec_url = clone_url
        if access_token and "github.com" in clone_url and "@" not in clone_url:
            exec_url = clone_url.replace("https://github.com", f"https://x-access-token:{access_token}@github.com")

        # Build the git command
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([exec_url, str(target_path)])

        logger.info("Cloning repository: %s → %s", clone_url, target_path)
        logger.debug("Git command: %s", " ".join(cmd))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                logger.error("Git clone failed (rc=%d): %s", proc.returncode, error_msg)
                # Clean up partial clone
                self._cleanup(target_path)
                raise RuntimeError(
                    f"Failed to clone repository '{url}': {error_msg}"
                )

            logger.info(
                "Successfully cloned %s/%s to %s", owner, repo_name, target_path
            )
            return target_path

        except FileNotFoundError:
            # git binary is not installed / not on PATH
            self._cleanup(target_path)
            raise RuntimeError(
                "'git' is not installed or not found on the system PATH."
            )
        except Exception:
            self._cleanup(target_path)
            raise

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cleanup(path: Path) -> None:
        """Silently remove *path* if it exists."""
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            logger.debug("Cleaned up partial clone at %s", path)
