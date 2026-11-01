"""
Application configuration using Pydantic Settings.

All settings can be overridden via environment variables or a .env file.
Sensible defaults are provided for local development.
"""

from typing import Any, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the RepoPilot application."""

    PROJECT_NAME: str = "RepoPilot"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "t", "yes", "y", "debug")
        return bool(v)


    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://repopilot:repopilot@localhost:5432/repopilot"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql://repopilot:repopilot@localhost:5432/repopilot"
    )

    # ── Vector DB (Qdrant) ────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "repo_chunks"

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── LLM (Google Gemini) ───────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-2.5-flash"

    # ── Embeddings ────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ── Storage ───────────────────────────────────────────────────────────
    REPOS_DIR: str = "./data/repos"
    UPLOADS_DIR: str = "./data/uploads"

    # ── Auth ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── GitHub OAuth ──────────────────────────────────────────────────────
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # ── Ingestion ─────────────────────────────────────────────────────────
    MAX_FILE_SIZE_KB: int = 500
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 200

    SUPPORTED_EXTENSIONS: list[str] = [
        # Python / general-purpose
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb",
        ".cpp", ".c", ".h", ".hpp", ".cs", ".php", ".swift", ".kt", ".scala",
        # Web / UI
        ".html", ".css", ".scss", ".less", ".vue", ".svelte",
        # Data / API
        ".sql", ".graphql", ".proto",
        # Config
        ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".env",
        # Docs
        ".md", ".rst", ".txt", ".dockerfile",
        # Shell
        ".sh", ".bash", ".zsh", ".fish",
        # Markup
        ".xml",
        # Other languages
        ".r", ".R", ".jl", ".lua", ".dart", ".ex", ".exs", ".erl", ".hs",
        # IaC
        ".tf", ".hcl",
    ]

    IGNORED_DIRS: list[str] = [
        ".git", "node_modules", "dist", "build", "venv", ".venv",
        "__pycache__", ".tox", ".mypy_cache", ".pytest_cache",
        "vendor", ".next", "target", "bin", "obj", ".idea", ".vscode",
        "coverage", ".nyc_output", "eggs", ".eggs",
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Singleton instance used across the application
settings = Settings()
