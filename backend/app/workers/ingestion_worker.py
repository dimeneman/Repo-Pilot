"""
Ingestion worker — asynchronous background pipeline for cloning, parsing, chunking, embedding, and indexing.
"""
from __future__ import annotations

import datetime
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.ingestion.chunker import CodeChunker
from app.ingestion.cloner import RepoCloner
from app.ingestion.file_filter import FileFilter
from app.ingestion.parser import FileParser
from app.models.chunk import Chunk
from app.models.file import File
from app.models.job import Job
from app.models.repository import Repository
from app.retrieval.embedding_service import EmbeddingService
from app.retrieval.vector_store import VectorStoreService

logger = get_logger(__name__)


class IngestionWorker:
    """Executes repository cloning, parsing, chunking, embedding, and indexing jobs."""

    def __init__(
        self,
        cloner: Optional[RepoCloner] = None,
        file_filter: Optional[FileFilter] = None,
        parser: Optional[FileParser] = None,
        chunker: Optional[CodeChunker] = None,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStoreService] = None,
    ):
        self.cloner = cloner or RepoCloner()
        self.file_filter = file_filter or FileFilter()
        self.parser = parser or FileParser()
        self.chunker = chunker or CodeChunker()
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStoreService()

    async def run_ingestion(self, repo_id_str: str, access_token: Optional[str] = None) -> None:
        """Run the full ingestion pipeline in the background."""
        repo_id = uuid.UUID(repo_id_str)

        async with async_session_factory() as db:
            repo = await db.get(Repository, repo_id)
            if not repo:
                logger.error(f"Ingestion worker: repo {repo_id} not found.")
                return

            # Create or reuse existing Job
            job = Job(
                repo_id=repo.id,
                job_type="ingest",
                status="running",
                progress=0.05,
                total_steps=10,
                current_step=1,
                step_description="Initiating repository ingestion",
                started_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(job)
            repo.status = "cloning"
            await db.commit()
            await db.refresh(job)

            repo_dir: Optional[Path] = None

            try:
                # STEP 1: Cloning repository
                logger.info(f"Cloning {repo.url} ({repo.default_branch})")
                job.current_step = 2
                job.progress = 0.15
                job.step_description = f"Cloning repository {repo.owner}/{repo.name}"
                await db.commit()

                target_dir = Path(settings.REPOS_DIR) / f"{repo.owner}_{repo.name}_{repo.id}"
                repo_dir = await self.cloner.clone_repository(
                    url=repo.url,
                    branch=repo.default_branch or "main",
                    target_dir=str(target_dir),
                    access_token=access_token,
                )

                # STEP 2: Filtering files
                job.current_step = 3
                job.progress = 0.30
                job.step_description = "Scanning and filtering source files"
                repo.status = "parsing"
                await db.commit()

                valid_files = self.file_filter.filter_repository(repo_dir)
                logger.info(f"Filtered {len(valid_files)} eligible files for repo {repo_id}")

                # STEP 3: Parsing files and creating File records
                job.current_step = 4
                job.progress = 0.45
                job.step_description = f"Parsing {len(valid_files)} source files"
                await db.commit()

                # Clean up existing files and vectors for this repo (for re-index or retry)
                await db.execute(delete(File).where(File.repo_id == repo.id))
                await db.commit()
                try:
                    await self.vector_store.delete_by_repo(str(repo.id))
                except Exception as exc:
                    logger.warning(f"Could not purge existing vectors for repo {repo.id}: {exc}")

                parsed_files = []
                file_models: List[File] = []
                language_counts: Dict[str, int] = {}

                for fpath in valid_files:
                    parsed = self.parser.parse_file(fpath, repo_dir)
                    parsed_files.append(parsed)

                    lang = parsed.language or "Unknown"
                    language_counts[lang] = language_counts.get(lang, 0) + 1

                    f_model = File(
                        repo_id=repo.id,
                        path=parsed.relative_path,
                        language=parsed.language,
                        size=parsed.size,
                        checksum=parsed.checksum,
                        line_count=parsed.line_count,
                    )
                    file_models.append(f_model)
                    db.add(f_model)

                await db.commit()
                # Refresh file models to get primary keys
                for f_model in file_models:
                    await db.refresh(f_model)

                file_lookup = {f.path: f.id for f in file_models}

                # STEP 4: Chunking files
                job.current_step = 5
                job.progress = 0.60
                job.step_description = "Extracting code-aware semantic chunks"
                repo.status = "indexing"
                await db.commit()

                all_chunks_payload = []
                chunk_texts_to_embed = []
                chunk_models: List[Chunk] = []

                for parsed in parsed_files:
                    chunks = self.chunker.chunk_file(
                        parsed,
                        chunk_size=settings.CHUNK_SIZE,
                        chunk_overlap=settings.CHUNK_OVERLAP,
                    )
                    file_id = file_lookup.get(parsed.relative_path)
                    if not file_id:
                        continue

                    for c in chunks:
                        chunk_id = uuid.uuid4()
                        c_model = Chunk(
                            id=chunk_id,
                            file_id=file_id,
                            repo_id=repo.id,
                            chunk_index=c.chunk_index,
                            start_line=c.start_line,
                            end_line=c.end_line,
                            content=c.content,
                            token_count=c.token_count,
                            chunk_type=c.chunk_type,
                            embedding_id=str(chunk_id),
                        )
                        chunk_models.append(c_model)
                        db.add(c_model)

                        chunk_texts_to_embed.append(c.content)
                        all_chunks_payload.append({
                            "id": str(chunk_id),
                            "file_id": str(file_id),
                            "file_path": parsed.relative_path,
                            "start_line": c.start_line,
                            "end_line": c.end_line,
                            "content": c.content,
                            "language": parsed.language,
                            "chunk_type": c.chunk_type,
                            "chunk_index": c.chunk_index,
                        })

                await db.commit()

                # STEP 5: Generating vector embeddings
                job.current_step = 7
                job.progress = 0.75
                job.step_description = f"Generating vector embeddings for {len(chunk_texts_to_embed)} chunks"
                await db.commit()

                embeddings = self.embedding_service.encode(chunk_texts_to_embed)

                # STEP 6: Indexing in Vector Store
                job.current_step = 9
                job.progress = 0.90
                job.step_description = "Upserting vectors into vector database"
                await db.commit()

                await self.vector_store.ensure_collection()
                await self.vector_store.upsert_embeddings(
                    chunks=all_chunks_payload,
                    embeddings=embeddings,
                    repo_id=str(repo.id),
                )

                # STEP 7: Finalizing repository metadata
                repo.file_count = len(file_models)
                repo.chunk_count = len(chunk_models)
                repo.language_stats = language_counts
                repo.status = "ready"
                repo.last_indexed_at = datetime.datetime.now(datetime.timezone.utc)
                repo.error_message = None

                job.status = "completed"
                job.progress = 1.0
                job.current_step = 10
                job.step_description = f"Successfully indexed {len(file_models)} files and {len(chunk_models)} chunks"
                job.completed_at = datetime.datetime.now(datetime.timezone.utc)
                await db.commit()

                logger.info(
                    f"Repository {repo.owner}/{repo.name} successfully indexed "
                    f"({len(file_models)} files, {len(chunk_models)} chunks)."
                )

            except Exception as exc:
                logger.exception(f"Ingestion failed for repo {repo_id}: {exc}")
                repo.status = "failed"
                repo.error_message = str(exc)

                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.datetime.now(datetime.timezone.utc)
                await db.commit()


# Helper function to invoke from FastAPI background tasks or CLI
async def run_ingestion(repo_id_str: str, access_token: Optional[str] = None) -> None:
    worker = IngestionWorker()
    await worker.run_ingestion(repo_id_str, access_token=access_token)

