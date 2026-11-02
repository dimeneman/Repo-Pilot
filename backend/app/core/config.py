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

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: Any = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://repo-pilot-steel.vercel.app",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if item]
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(item).strip() for item in v if item]
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://repo-pilot-steel.vercel.app",
        ]


    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://repopilot:repopilot@localhost:5432/repopilot"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql://repopilot:repopilot@localhost:5432/repopilot"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Any) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return str(v)

    @field_validator("DATABASE_URL_SYNC", mode="before")
    @classmethod
    def normalize_database_url_sync(cls, v: Any) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql://", 1)
            if v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql+asyncpg://", "postgresql://", 1)
        return str(v)

    # ── Vector DB (Qdrant) ────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "repo_chunks"

    # ── Redis & Background Worker ─────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    RUN_EMBEDDED_WORKER: bool = False
    WORKER_POLL_INTERVAL: float = 2.0

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

    # ── GitHub Actions Ingestion Runner (Production Background Worker) ────
    INGESTION_RUNNER: str = "auto"  # "auto", "github_actions", "direct", or "local"
    GITHUB_ACTIONS_TOKEN: Optional[str] = None
    GITHUB_REPO_OWNER: str = "dimeneman"
    GITHUB_REPO_NAME: str = "Repo-Pilot"
    GITHUB_WORKFLOW_EVENT_TYPE: str = "ingest_repo"

    @field_validator("GITHUB_ACTIONS_TOKEN", mode="before")
    @classmethod
    def fallback_actions_token(cls, v: Any) -> Optional[str]:
        if not v or (isinstance(v, str) and not v.strip()):
            import os
            token = os.environ.get("GITHUB_ACTIONS_TOKEN") or os.environ.get("GITHUB_TOKEN")
            return token.strip() if token and token.strip() else None
        return str(v).strip()

    @field_validator("GITHUB_REPO_OWNER", mode="before")
    @classmethod
    def fallback_owner(cls, v: Any) -> str:
        if not v or (isinstance(v, str) and not v.strip()):
            import os
            repo_env = os.environ.get("GITHUB_REPOSITORY", "")
            if "/" in repo_env:
                return repo_env.split("/")[0].strip()
            return "dimeneman"
        return str(v).strip()

    @field_validator("GITHUB_REPO_NAME", mode="before")
    @classmethod
    def fallback_repo_name(cls, v: Any) -> str:
        if not v or (isinstance(v, str) and not v.strip()):
            import os
            repo_env = os.environ.get("GITHUB_REPOSITORY", "")
            if "/" in repo_env:
                return repo_env.split("/")[1].strip()
            return "Repo-Pilot"
        return str(v).strip()

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
