"""
Pytest configuration and fixtures.
"""
from __future__ import annotations

import os
import uuid
from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set testing environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///:memory:"
os.environ["DEBUG"] = "true"
os.environ["EMBEDDING_MODEL"] = "fallback"


from app.core.config import settings
from app.retrieval.embedding_service import EmbeddingService
settings.EMBEDDING_MODEL = "fallback"
settings.GEMINI_API_KEY = ""
EmbeddingService._instance = None

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.chunk import Chunk
from app.models.file import File
from app.models.repository import Repository
from app.retrieval.vector_store import VectorStoreService

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture
async def prepare_database():
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(prepare_database) -> AsyncGenerator[AsyncSession, None]:
    """Yield a test session bound to the in-memory test database."""
    async with TestSessionLocal() as session:
        yield session



@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient with overridden database dependency."""
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_repo(db_session: AsyncSession) -> Repository:
    """Seed a sample repository for testing."""
    repo = Repository(
        id=uuid.uuid4(),
        url="https://github.com/repopilot/test-repo",
        name="test-repo",
        owner="repopilot",
        default_branch="main",
        status="ready",
        file_count=2,
        chunk_count=3,
        language_stats={"Python": 2},
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    file_record = File(
        id=uuid.uuid4(),
        repo_id=repo.id,
        path="src/auth.py",
        language="Python",
        size=350,
        checksum="abcdef123456",
        line_count=25,
    )
    db_session.add(file_record)
    await db_session.commit()
    await db_session.refresh(file_record)

    chunk = Chunk(
        id=uuid.uuid4(),
        file_id=file_record.id,
        repo_id=repo.id,
        chunk_index=0,
        start_line=1,
        end_line=25,
        content="def authenticate_user(username: str, token: str) -> bool:\n    return token == 'secret'",
        token_count=18,
        chunk_type="code",
        embedding_id="mock-chunk-1",
    )
    db_session.add(chunk)
    await db_session.commit()

    return repo

