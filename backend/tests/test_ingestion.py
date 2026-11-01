"""Unit tests for ingestion components: cloner, filter, parser."""
from pathlib import Path
from app.ingestion.cloner import RepoCloner
from app.ingestion.file_filter import FileFilter
from app.ingestion.parser import FileParser


def test_parse_github_url():
    """Verify various GitHub URL formats parse correctly."""
    cloner = RepoCloner()
    
    owner, name = cloner.parse_github_url("https://github.com/torvalds/linux")
    assert owner == "torvalds"
    assert name == "linux"

    owner2, name2 = cloner.parse_github_url("https://github.com/fastapi/fastapi.git")
    assert owner2 == "fastapi"
    assert name2 == "fastapi"

    owner3, name3 = cloner.parse_github_url("github.com/facebook/react")
    assert owner3 == "facebook"
    assert name3 == "react"


def test_file_filtering_and_language_detection(tmp_path: Path):
    """Verify filtering ignores unwanted directories and handles extensions."""
    # Create allowed file
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    py_file = src_dir / "main.py"
    py_file.write_text("print('hello world')")

    # Create ignored folder and file
    ignored_dir = tmp_path / "node_modules" / "pkg"
    ignored_dir.mkdir(parents=True)
    ignored_file = ignored_dir / "index.js"
    ignored_file.write_text("console.log('ignored')")

    filter_service = FileFilter()
    filtered = filter_service.filter_repository(tmp_path)

    assert py_file in filtered
    assert ignored_file not in filtered

    # Verify parser
    parser = FileParser()
    parsed = parser.parse_file(py_file, tmp_path)
    assert parsed.relative_path == "src/main.py"
    assert parsed.language == "Python"
    assert parsed.line_count == 1
    assert len(parsed.checksum) == 64

