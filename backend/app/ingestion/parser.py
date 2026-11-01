"""
File parser — reads source files and extracts metadata.

Handles encoding detection/fallback, line counting, checksumming,
and language detection.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from app.core.logging import get_logger
from app.ingestion.file_filter import FileFilter

logger = get_logger(__name__)


@dataclass(frozen=True)
class ParsedFile:
    """Immutable representation of a parsed source file.

    Attributes:
        relative_path: Path relative to the repository root.
        content: Full text content of the file.
        language: Detected programming language.
        size: File size in bytes.
        line_count: Total number of lines.
        checksum: SHA-256 hex digest of the file content.
    """

    relative_path: str
    content: str
    language: str
    size: int
    line_count: int
    checksum: str


class FileParser:
    """Reads and parses source files, producing :class:`ParsedFile` instances.

    Handles encoding gracefully — tries UTF-8 first, then falls back to
    Latin-1 (which never raises a decode error because every byte maps to
    a valid character).
    """

    # Encodings to try in order.  latin-1 is guaranteed to succeed.
    _ENCODINGS = ("utf-8", "latin-1")

    def parse_file(self, file_path: Path, repo_root: Path) -> ParsedFile:
        """Parse a single file and return its metadata.

        Args:
            file_path: Absolute path to the source file.
            repo_root: Root directory of the cloned repository.

        Returns:
            A :class:`ParsedFile` with content and metadata.

        Raises:
            FileNotFoundError: If *file_path* does not exist.
            OSError: For unexpected I/O errors that survive encoding
                fallback.
        """
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read content with encoding fallback
        content = self._read_with_fallback(file_path)

        # Compute metadata
        relative_path = str(file_path.relative_to(repo_root))
        size = file_path.stat().st_size
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        language = FileFilter.detect_language(file_path)

        logger.debug(
            "Parsed %s — %s, %d lines, %d bytes",
            relative_path,
            language,
            line_count,
            size,
        )

        return ParsedFile(
            relative_path=relative_path,
            content=content,
            language=language,
            size=size,
            line_count=line_count,
            checksum=checksum,
        )

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    @staticmethod
    def _read_with_fallback(file_path: Path) -> str:
        """Read *file_path* trying multiple encodings.

        Returns:
            Decoded string content.
        """
        for encoding in FileParser._ENCODINGS:
            try:
                return file_path.read_text(encoding=encoding)
            except (UnicodeDecodeError, ValueError):
                logger.debug(
                    "Encoding %s failed for %s, trying next", encoding, file_path
                )
                continue

        # Should never reach here since latin-1 handles all byte values,
        # but guard anyway.
        return file_path.read_text(encoding="utf-8", errors="replace")
