#!/usr/bin/env python3
"""
Seed demo data for development and testing.

Creates sample repositories with realistic files, chunks, and queries.
"""
import asyncio
import sys
import uuid
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.db.session import async_session_factory, init_db
from app.models.chunk import Chunk
from app.models.file import File
from app.models.query import Query
from app.models.repository import Repository
from app.retrieval.embedding_service import EmbeddingService
from app.retrieval.vector_store import VectorStoreService


async def seed():
    print("🌱 Initializing database and vector store...")
    await init_db()

    vs = VectorStoreService()
    await vs.ensure_collection()
    embedder = EmbeddingService()

    async with async_session_factory() as db:
        print("🌱 Creating sample repository 'fastapi-microservice'...")
        repo = Repository(
            id=uuid.uuid4(),
            url="https://github.com/repopilot-demo/fastapi-microservice",
            name="fastapi-microservice",
            owner="repopilot-demo",
            default_branch="main",
            status="ready",
            file_count=3,
            chunk_count=3,
            language_stats={"Python": 2, "Dockerfile": 1},
        )
        db.add(repo)
        await db.commit()

        # Files
        auth_file = File(
            id=uuid.uuid4(),
            repo_id=repo.id,
            path="app/core/security.py",
            language="Python",
            size=1200,
            checksum="hash1",
            line_count=45,
        )
        db.add(auth_file)

        api_file = File(
            id=uuid.uuid4(),
            repo_id=repo.id,
            path="app/api/v1/auth.py",
            language="Python",
            size=1800,
            checksum="hash2",
            line_count=60,
        )
        db.add(api_file)
        await db.commit()

        # Chunks
        chunk1_text = """def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")"""

        chunk2_text = """@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}"""

        c1_id = uuid.uuid4()
        c2_id = uuid.uuid4()

        c1 = Chunk(
            id=c1_id,
            file_id=auth_file.id,
            repo_id=repo.id,
            chunk_index=0,
            start_line=15,
            end_line=30,
            content=chunk1_text,
            token_count=85,
            chunk_type="code",
            embedding_id=str(c1_id),
        )
        c2 = Chunk(
            id=c2_id,
            file_id=api_file.id,
            repo_id=repo.id,
            chunk_index=0,
            start_line=20,
            end_line=35,
            content=chunk2_text,
            token_count=90,
            chunk_type="code",
            embedding_id=str(c2_id),
        )
        db.add(c1)
        db.add(c2)
        await db.commit()

        # Vector indexing
        embeddings = embedder.encode([chunk1_text, chunk2_text])
        await vs.upsert_embeddings(
            chunks=[
                {
                    "id": str(c1_id),
                    "file_id": str(auth_file.id),
                    "file_path": auth_file.path,
                    "start_line": 15,
                    "end_line": 30,
                    "content": chunk1_text,
                    "language": "Python",
                    "chunk_type": "code",
                },
                {
                    "id": str(c2_id),
                    "file_id": str(api_file.id),
                    "file_path": api_file.path,
                    "start_line": 20,
                    "end_line": 35,
                    "content": chunk2_text,
                    "language": "Python",
                    "chunk_type": "code",
                },
            ],
            embeddings=embeddings,
            repo_id=str(repo.id),
        )

        print(f"✅ Demo repository seeded with ID: {repo.id}")


if __name__ == "__main__":
    asyncio.run(seed())

