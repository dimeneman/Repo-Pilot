"""
File filter — walks a repository tree and returns files suitable for indexing.

Applies extension whitelist, directory blacklist, size limits, and binary
detection to keep only meaningful source / documentation files.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import List

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Map file extensions to human-readable language names.
_EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".h": "C",
    ".hpp": "C++",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".r": "R",
    ".R": "R",
    ".lua": "Lua",
    ".pl": "Perl",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".fish": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SASS",
    ".less": "LESS",
    ".xml": "XML",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".ini": "INI",
    ".cfg": "INI",
    ".md": "Markdown",
    ".mdx": "Markdown",
    ".rst": "reStructuredText",
    ".txt": "Text",
    ".csv": "CSV",
    ".env": "Env",
    ".dockerfile": "Dockerfile",
    ".tf": "Terraform",
    ".hcl": "HCL",
    ".proto": "Protobuf",
    ".graphql": "GraphQL",
    ".gql": "GraphQL",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".ml": "OCaml",
    ".clj": "Clojure",
    ".jl": "Julia",
    ".m": "Objective-C",
    ".makefile": "Makefile",
}

# Files matched by basename (case-insensitive) that lack an extension.
_KNOWN_FILENAMES: dict[str, str] = {
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "cmakelists.txt": "CMake",
    "gemfile": "Ruby",
    "rakefile": "Ruby",
    "procfile": "Procfile",
    "vagrantfile": "Ruby",
    "justfile": "Makefile",
    "taskfile": "YAML",
}

# Byte sequences that strongly indicate a binary file.
_BINARY_MARKER_BYTES = b"\x00"

# Sampling size (bytes) when checking for binary content.
_BINARY_CHECK_SIZE = 8192


class FileFilter:
    """Filters a repository's file tree to keep only indexable source files.

    Applies the following rules in order:
    1. Skip directories in ``settings.IGNORED_DIRS``.
    2. Only include files whose extension is in ``settings.SUPPORTED_EXTENSIONS``.
    3. Skip files larger than ``settings.MAX_FILE_SIZE_KB`` kilobytes.
    4. Skip files detected as binary.
    """

    def __init__(self) -> None:
        # Pre-process settings for fast lookups
        self._ignored_dirs: set[str] = set(settings.IGNORED_DIRS)
        self._supported_exts: set[str] = {
            ext if ext.startswith(".") else f".{ext}"
            for ext in settings.SUPPORTED_EXTENSIONS
        }
        self._max_size_bytes: int = settings.MAX_FILE_SIZE_KB * 1024

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def filter_repository(self, repo_path: Path) -> List[Path]:
        """Walk *repo_path* and return a sorted list of indexable files.

        Args:
            repo_path: Root directory of the cloned repository.

        Returns:
            Sorted list of absolute :class:`~pathlib.Path` objects.
        """
        if not repo_path.is_dir():
            logger.warning("Repository path does not exist: %s", repo_path)
            return []

        valid_files: list[Path] = []

        for file_path in sorted(repo_path.rglob("*")):
            if not file_path.is_file():
                continue

            # 1. Check ignored directories
            if self._in_ignored_dir(file_path, repo_path):
                continue

            # 2. Check extension (or known filename)
            if not self._has_supported_extension(file_path):
                continue

            # 3. Check file size
            try:
                file_size = file_path.stat().st_size
            except OSError:
                logger.debug("Cannot stat file, skipping: %s", file_path)
                continue

            if file_size > self._max_size_bytes:
                logger.debug(
                    "File exceeds size limit (%d KB > %d KB): %s",
                    file_size // 1024,
                    settings.MAX_FILE_SIZE_KB,
                    file_path,
                )
                continue

            if file_size == 0:
                continue

            # 4. Check binary content
            if self.is_binary(file_path):
                logger.debug("Binary file skipped: %s", file_path)
                continue

            valid_files.append(file_path)

        logger.info(
            "Filtered repository %s: %d files accepted", repo_path.name, len(valid_files)
        )
        return valid_files

    # ------------------------------------------------------------------ #
    # Language detection
    # ------------------------------------------------------------------ #

    @staticmethod
    def detect_language(file_path: Path) -> str:
        """Detect the programming language based on file extension or name.

        Args:
            file_path: Path to the file.

        Returns:
            Human-readable language name, or ``"Unknown"`` if unrecognised.
        """
        ext = file_path.suffix.lower()
        if ext in _EXTENSION_LANGUAGE_MAP:
            return _EXTENSION_LANGUAGE_MAP[ext]

        # Try matching by known filename (case-insensitive)
        basename = file_path.name.lower()
        if basename in _KNOWN_FILENAMES:
            return _KNOWN_FILENAMES[basename]

        # Last resort – try mimetypes
        mime, _ = mimetypes.guess_type(str(file_path))
        if mime and mime.startswith("text/"):
            return "Text"

        return "Unknown"

    # ------------------------------------------------------------------ #
    # Binary detection
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_binary(file_path: Path) -> bool:
        """Heuristically determine if *file_path* is a binary file.

        Reads the first ``_BINARY_CHECK_SIZE`` bytes and checks for null
        bytes — a strong indicator of binary content.
        """
        try:
            with open(file_path, "rb") as fh:
                chunk = fh.read(_BINARY_CHECK_SIZE)
            return _BINARY_MARKER_BYTES in chunk
        except (OSError, PermissionError):
            return True  # Treat unreadable files as binary

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _in_ignored_dir(self, file_path: Path, repo_root: Path) -> bool:
        """Return *True* if any ancestor directory of *file_path* (relative
        to *repo_root*) is in the ignore list."""
        try:
            relative = file_path.relative_to(repo_root)
        except ValueError:
            return False
        return any(part in self._ignored_dirs for part in relative.parts[:-1])

    def _has_supported_extension(self, file_path: Path) -> bool:
        """Return *True* if the file extension or name is supported."""
        ext = file_path.suffix.lower()
        if ext and ext in self._supported_exts:
            return True
        # Also match known filenames without extensions
        return file_path.name.lower() in _KNOWN_FILENAMES
