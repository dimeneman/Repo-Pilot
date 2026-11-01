"""
Code-aware chunker — splits source files into semantically meaningful chunks.

Strategy hierarchy:
1. **Code files**: Detect function / class boundaries via language-specific
   regex patterns and split at those boundaries.  If a single definition
   exceeds *chunk_size* tokens it is further split with overlap.
2. **Markdown / documentation**: Split on heading boundaries (``##``, ``###``).
3. **Config files** (JSON, YAML, TOML, INI): Keep whole if small enough,
   otherwise split on top-level keys / blank-line sections.
4. **Fallback**: Line-based splitting with token-aware sizing and overlap.

Token counting uses *tiktoken* (``cl100k_base`` encoding) so that chunk
sizes map closely to LLM context windows.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

import tiktoken

from app.core.logging import get_logger
from app.ingestion.parser import ParsedFile

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Token counter (lazy-loaded singleton)
# ---------------------------------------------------------------------------
_tokenizer: Optional[tiktoken.Encoding] = None


def _get_tokenizer() -> Optional[tiktoken.Encoding]:
    """Return a cached ``cl100k_base`` tiktoken encoder, or None if offline."""
    global _tokenizer
    if _tokenizer is None:
        try:
            _tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None
    return _tokenizer


def count_tokens(text: str) -> int:
    """Count the number of tokens in *text* using ``cl100k_base`` (or character-ratio fallback)."""
    try:
        tok = _get_tokenizer()
        if tok is not None:
            return len(tok.encode(text, disallowed_special=()))
    except Exception:
        pass
    # Robust fallback: ~4 characters per token for standard code/text
    return max(1, len(text) // 4)



# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CodeChunk:
    """A single chunk produced by the code-aware chunker.

    Attributes:
        content: The raw text of the chunk.
        start_line: 1-indexed first line of the chunk in the source file.
        end_line: 1-indexed last line of the chunk in the source file.
        chunk_index: Sequential index within the file.
        chunk_type: One of ``"code"``, ``"doc"``, ``"config"``.
        token_count: Number of tokens in *content*.
    """

    content: str
    start_line: int
    end_line: int
    chunk_index: int
    chunk_type: str
    token_count: int


# ---------------------------------------------------------------------------
# Language-specific boundary patterns
# ---------------------------------------------------------------------------
# Each pattern is designed to match the *start* of a function / class /
# method / module-level definition.  We compile once at import time.

_BOUNDARY_PATTERNS: dict[str, re.Pattern] = {
    "Python": re.compile(
        r"^(?:async\s+)?(?:def|class)\s+\w+", re.MULTILINE
    ),
    "JavaScript": re.compile(
        r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\*?\s+\w+|class\s+\w+|const\s+\w+\s*=\s*(?:async\s+)?\(|let\s+\w+\s*=\s*(?:async\s+)?\(|var\s+\w+\s*=\s*function)",
        re.MULTILINE,
    ),
    "TypeScript": re.compile(
        r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\*?\s+\w+|class\s+\w+|const\s+\w+\s*[:=]|interface\s+\w+|type\s+\w+\s*=|enum\s+\w+)",
        re.MULTILINE,
    ),
    "Java": re.compile(
        r"^\s*(?:public|private|protected|static|final|abstract|synchronized|native)?\s*(?:public|private|protected|static|final|abstract|synchronized|native)?\s*(?:class|interface|enum|void|int|String|boolean|long|double|float|byte|short|char|\w+)\s+\w+\s*[\({<]",
        re.MULTILINE,
    ),
    "Go": re.compile(
        r"^(?:func\s+(?:\(\w+\s+\*?\w+\)\s+)?\w+|type\s+\w+\s+(?:struct|interface))",
        re.MULTILINE,
    ),
    "Rust": re.compile(
        r"^(?:pub\s+)?(?:async\s+)?(?:fn\s+\w+|struct\s+\w+|enum\s+\w+|impl\s+(?:<[^>]+>\s+)?\w+|trait\s+\w+|mod\s+\w+)",
        re.MULTILINE,
    ),
    "C": re.compile(
        r"^(?:static\s+)?(?:inline\s+)?(?:const\s+)?(?:unsigned\s+)?(?:void|int|char|float|double|long|short|struct\s+\w+)\s+\*?\w+\s*\(",
        re.MULTILINE,
    ),
    "C++": re.compile(
        r"^(?:(?:static|inline|virtual|explicit|constexpr|template\s*<[^>]*>)\s+)*(?:class|struct|namespace|void|int|char|float|double|long|short|auto|bool|\w+(?:::\w+)*)\s+\*?\w+\s*[\({<]",
        re.MULTILINE,
    ),
    "C#": re.compile(
        r"^\s*(?:public|private|protected|internal|static|abstract|virtual|override|sealed|async)?\s*(?:public|private|protected|internal|static|abstract|virtual|override|sealed|async)?\s*(?:class|interface|struct|enum|void|int|string|bool|Task|async)\s+\w+",
        re.MULTILINE,
    ),
    "Ruby": re.compile(
        r"^(?:def\s+\w+|class\s+\w+|module\s+\w+)", re.MULTILINE
    ),
    "PHP": re.compile(
        r"^(?:(?:public|private|protected|static|abstract|final)\s+)*(?:function\s+\w+|class\s+\w+|interface\s+\w+|trait\s+\w+)",
        re.MULTILINE,
    ),
    "Kotlin": re.compile(
        r"^(?:(?:public|private|protected|internal|open|abstract|sealed|data|inline|suspend)\s+)*(?:fun\s+\w+|class\s+\w+|interface\s+\w+|object\s+\w+)",
        re.MULTILINE,
    ),
    "Swift": re.compile(
        r"^(?:(?:public|private|internal|open|fileprivate|static|class|override)\s+)*(?:func\s+\w+|class\s+\w+|struct\s+\w+|enum\s+\w+|protocol\s+\w+)",
        re.MULTILINE,
    ),
    "Scala": re.compile(
        r"^(?:(?:def|val|var|class|object|trait|case\s+class|abstract\s+class)\s+\w+)",
        re.MULTILINE,
    ),
    "Elixir": re.compile(
        r"^(?:def|defp|defmodule|defmacro)\s+\w+", re.MULTILINE
    ),
    "Dart": re.compile(
        r"^(?:(?:abstract|static|final)\s+)?(?:class\s+\w+|void\s+\w+|Future\s*<|Stream\s*<|\w+\s+\w+\s*\()",
        re.MULTILINE,
    ),
}

_DOC_LANGUAGES = {"Markdown", "reStructuredText", "Text"}
_CONFIG_LANGUAGES = {"JSON", "YAML", "TOML", "INI", "Env", "CSV", "XML"}

# Heading pattern for Markdown splitting
_MD_HEADING_PATTERN = re.compile(r"^#{1,6}\s+", re.MULTILINE)


class CodeChunker:
    """Splits a :class:`ParsedFile` into semantically meaningful chunks.

    The chunker is language-aware: it tries to split on function / class
    boundaries for code files, on headings for documentation, and on
    sections for config files.  When structural splitting is not possible
    or a block exceeds the target token size it falls back to
    line-based splitting with configurable overlap.
    """

    def chunk_file(
        self,
        parsed_file: ParsedFile,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> List[CodeChunk]:
        """Chunk *parsed_file* into a list of :class:`CodeChunk`.

        Args:
            parsed_file: The parsed source file to chunk.
            chunk_size: Target maximum tokens per chunk.
            chunk_overlap: Overlap in tokens between consecutive chunks
                (used when a single block must be further split).

        Returns:
            Ordered list of :class:`CodeChunk` instances.
        """
        language = parsed_file.language
        content = parsed_file.content

        if not content.strip():
            return []

        lines = content.split("\n")

        # Dispatch to the appropriate strategy
        if language in _DOC_LANGUAGES:
            raw_blocks = self._split_markdown(lines)
            chunk_type = "doc"
        elif language in _CONFIG_LANGUAGES:
            raw_blocks = self._split_config(lines)
            chunk_type = "config"
        elif language in _BOUNDARY_PATTERNS:
            raw_blocks = self._split_code(lines, language)
            chunk_type = "code"
        else:
            # Unknown language — treat as code with fallback splitting
            raw_blocks = self._split_fallback(lines, chunk_size, chunk_overlap)
            chunk_type = "code"

        # Post-process: enforce token limits and build CodeChunk objects
        chunks: list[CodeChunk] = []
        chunk_index = 0

        for block_start, block_end, block_lines in raw_blocks:
            block_text = "\n".join(block_lines)
            tokens = count_tokens(block_text)

            if tokens <= chunk_size:
                # Block fits within limits
                chunks.append(
                    CodeChunk(
                        content=block_text,
                        start_line=block_start,
                        end_line=block_end,
                        chunk_index=chunk_index,
                        chunk_type=chunk_type,
                        token_count=tokens,
                    )
                )
                chunk_index += 1
            else:
                # Block too large — sub-split with overlap
                sub_chunks = self._split_large_block(
                    block_lines,
                    block_start,
                    chunk_size,
                    chunk_overlap,
                    chunk_type,
                    chunk_index,
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)

        if not chunks:
            # Edge case: entire file is a single small block
            tokens = count_tokens(content)
            chunks.append(
                CodeChunk(
                    content=content,
                    start_line=1,
                    end_line=len(lines),
                    chunk_index=0,
                    chunk_type=chunk_type,
                    token_count=tokens,
                )
            )

        logger.debug(
            "Chunked %s (%s) into %d chunks",
            parsed_file.relative_path,
            language,
            len(chunks),
        )
        return chunks

    # ------------------------------------------------------------------ #
    # Strategy: Code (function / class boundary splitting)
    # ------------------------------------------------------------------ #

    def _split_code(
        self,
        lines: list[str],
        language: str,
    ) -> list[tuple[int, int, list[str]]]:
        """Split *lines* at function / class definition boundaries.

        Returns a list of ``(start_line_1idx, end_line_1idx, lines)`` tuples.
        """
        pattern = _BOUNDARY_PATTERNS[language]
        boundary_indices: list[int] = []

        for idx, line in enumerate(lines):
            if pattern.match(line):
                boundary_indices.append(idx)

        if not boundary_indices:
            # No boundaries detected – return entire file as one block
            return [(1, len(lines), lines)]

        blocks: list[tuple[int, int, list[str]]] = []

        # Leading content before the first boundary (imports, docstrings…)
        if boundary_indices[0] > 0:
            pre = lines[: boundary_indices[0]]
            if any(l.strip() for l in pre):  # skip if all-blank
                blocks.append((1, boundary_indices[0], pre))

        # Each boundary runs until the next boundary
        for i, start_idx in enumerate(boundary_indices):
            end_idx = (
                boundary_indices[i + 1] if i + 1 < len(boundary_indices) else len(lines)
            )
            block_lines = lines[start_idx:end_idx]
            # 1-indexed lines
            blocks.append((start_idx + 1, end_idx, block_lines))

        return blocks

    # ------------------------------------------------------------------ #
    # Strategy: Markdown heading splitting
    # ------------------------------------------------------------------ #

    def _split_markdown(
        self,
        lines: list[str],
    ) -> list[tuple[int, int, list[str]]]:
        """Split markdown content on heading lines (``# …``, ``## …``)."""
        heading_indices: list[int] = []

        for idx, line in enumerate(lines):
            if _MD_HEADING_PATTERN.match(line):
                heading_indices.append(idx)

        if not heading_indices:
            return [(1, len(lines), lines)]

        blocks: list[tuple[int, int, list[str]]] = []

        # Content before first heading
        if heading_indices[0] > 0:
            pre = lines[: heading_indices[0]]
            if any(l.strip() for l in pre):
                blocks.append((1, heading_indices[0], pre))

        for i, start_idx in enumerate(heading_indices):
            end_idx = (
                heading_indices[i + 1] if i + 1 < len(heading_indices) else len(lines)
            )
            block_lines = lines[start_idx:end_idx]
            blocks.append((start_idx + 1, end_idx, block_lines))

        return blocks

    # ------------------------------------------------------------------ #
    # Strategy: Config files
    # ------------------------------------------------------------------ #

    def _split_config(
        self,
        lines: list[str],
    ) -> list[tuple[int, int, list[str]]]:
        """Split config files on blank-line sections.

        If the entire config is small enough, return it as-is.
        """
        full_text = "\n".join(lines)
        if count_tokens(full_text) <= 512:
            return [(1, len(lines), lines)]

        # Split on double-newlines
        blocks: list[tuple[int, int, list[str]]] = []
        current_start = 0
        current_lines: list[str] = []

        for idx, line in enumerate(lines):
            if line.strip() == "" and current_lines:
                blocks.append((current_start + 1, idx, list(current_lines)))
                current_lines = []
                current_start = idx + 1
            else:
                if not current_lines:
                    current_start = idx
                current_lines.append(line)

        if current_lines:
            blocks.append((current_start + 1, len(lines), current_lines))

        return blocks if blocks else [(1, len(lines), lines)]

    # ------------------------------------------------------------------ #
    # Fallback: line-based splitting
    # ------------------------------------------------------------------ #

    def _split_fallback(
        self,
        lines: list[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[tuple[int, int, list[str]]]:
        """Split *lines* by line count, targeting *chunk_size* tokens."""
        if not lines:
            return []

        # Estimate lines-per-chunk from average tokens-per-line
        full_text = "\n".join(lines)
        total_tokens = count_tokens(full_text)

        if total_tokens <= chunk_size:
            return [(1, len(lines), lines)]

        avg_tokens_per_line = max(total_tokens / max(len(lines), 1), 1)
        lines_per_chunk = max(int(chunk_size / avg_tokens_per_line), 5)
        overlap_lines = max(int(chunk_overlap / avg_tokens_per_line), 1)
        # Ensure overlap is strictly less than lines_per_chunk so step is always >= 1
        overlap_lines = min(overlap_lines, lines_per_chunk - 1)
        step = max(lines_per_chunk - overlap_lines, 1)

        blocks: list[tuple[int, int, list[str]]] = []
        start = 0

        while start < len(lines):
            end = min(start + lines_per_chunk, len(lines))
            block_lines = lines[start:end]
            blocks.append((start + 1, end, block_lines))
            if end >= len(lines):
                break
            start += step

        return blocks

    # ------------------------------------------------------------------ #
    # Sub-splitting oversized blocks
    # ------------------------------------------------------------------ #

    def _split_large_block(
        self,
        block_lines: list[str],
        global_start_line: int,
        chunk_size: int,
        chunk_overlap: int,
        chunk_type: str,
        starting_index: int,
    ) -> list[CodeChunk]:
        """Split an oversized block into sub-chunks with overlap.

        Uses line-based splitting but respects the token budget.
        """
        sub_blocks = self._split_fallback(block_lines, chunk_size, chunk_overlap)

        chunks: list[CodeChunk] = []
        for i, (local_start, local_end, sub_lines) in enumerate(sub_blocks):
            text = "\n".join(sub_lines)
            tokens = count_tokens(text)
            chunks.append(
                CodeChunk(
                    content=text,
                    start_line=global_start_line + local_start - 1,
                    end_line=global_start_line + local_end - 1,
                    chunk_index=starting_index + i,
                    chunk_type=chunk_type,
                    token_count=tokens,
                )
            )
        return chunks
