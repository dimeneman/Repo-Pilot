"""Unit tests for the code-aware chunker."""
import pytest
from app.ingestion.chunker import CodeChunker, count_tokens
from app.ingestion.parser import ParsedFile


def test_token_counting():
    """Verify that token counting works."""
    text = "def hello_world(): return 'hello'"
    count = count_tokens(text)
    assert count > 0


def test_chunk_python_functions():
    """Verify chunker detects function definitions in Python code."""
    code = """
import os

def calculate_sum(a: int, b: int) -> int:
    # First function
    return a + b

def calculate_product(x: int, y: int) -> int:
    # Second function
    return x * y

class MathService:
    def __init__(self):
        pass
"""
    parsed = ParsedFile(
        relative_path="math_service.py",
        content=code,
        language="Python",
        size=len(code),
        line_count=15,
        checksum="dummy",
    )
    chunker = CodeChunker()
    chunks = chunker.chunk_file(parsed, chunk_size=100, chunk_overlap=10)

    assert len(chunks) >= 2
    assert chunks[0].start_line >= 1
    assert chunks[0].end_line >= chunks[0].start_line
    assert any("calculate_sum" in c.content for c in chunks)
    assert any("calculate_product" in c.content for c in chunks)


def test_chunk_markdown_headings():
    """Verify markdown files are split along headings."""
    doc = """# Main Title

Introduction to the platform.

## Architecture

The system uses Next.js and FastAPI.

## Getting Started

Run docker compose up to start.
"""
    parsed = ParsedFile(
        relative_path="docs/overview.md",
        content=doc,
        language="Markdown",
        size=len(doc),
        line_count=12,
        checksum="dummy2",
    )
    chunker = CodeChunker()
    chunks = chunker.chunk_file(parsed, chunk_size=50, chunk_overlap=5)

    assert len(chunks) >= 2
    assert any("Architecture" in c.content for c in chunks)


def test_split_fallback_no_infinite_loop():
    """Verify fallback line-based chunker always terminates cleanly and covers all lines."""
    chunker = CodeChunker()
    lines = [f"line {i}: some code content that takes a few tokens" for i in range(1, 501)]

    # Test various chunk_size and chunk_overlap combinations
    blocks = chunker._split_fallback(lines, chunk_size=50, chunk_overlap=10)
    assert len(blocks) > 0
    # Verify the last block reaches line 500
    assert blocks[-1][1] == 500
    # Verify progression
    for i in range(len(blocks) - 1):
        assert blocks[i][0] < blocks[i + 1][0]
        assert blocks[i][1] <= blocks[i + 1][1]


def test_chunk_unknown_language_fallback():
    """Verify unknown language files are split safely with fallback."""
    chunker = CodeChunker()
    content = "\n".join([f"key_{i} = value_{i} # arbitrary text" for i in range(200)])
    parsed = ParsedFile(
        relative_path="data.unknown",
        content=content,
        language="Unknown",
        size=len(content),
        line_count=200,
        checksum="dummy3",
    )
    chunks = chunker.chunk_file(parsed, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == 200


def test_split_large_block_sub_split():
    """Verify an oversized function definition is cleanly sub-split."""
    chunker = CodeChunker()
    # A single huge function with 300 lines
    code_lines = ["def huge_function():"] + [f"    x_{i} = {i} * 2" for i in range(300)]
    content = "\n".join(code_lines)
    parsed = ParsedFile(
        relative_path="service.py",
        content=content,
        language="Python",
        size=len(content),
        line_count=len(code_lines),
        checksum="dummy4",
    )
    chunks = chunker.chunk_file(parsed, chunk_size=150, chunk_overlap=20)
    assert len(chunks) > 1
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == len(code_lines)


