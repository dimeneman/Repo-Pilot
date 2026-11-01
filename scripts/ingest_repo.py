#!/usr/bin/env python3
"""
CLI script to ingest a GitHub repository into RepoPilot.

Usage:
    python scripts/ingest_repo.py --url https://github.com/fastapi/fastapi --branch master
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.logging import get_logger
from app.db.session import async_session_factory, init_db
from app.models.repository import Repository
from app.schemas.repository import RepoIngestRequest
from app.services.repository_service import RepositoryService
from app.workers.ingestion_worker import IngestionWorker

logger = get_logger("cli.ingest")


async def main():
    parser = argparse.ArgumentParser(description="Ingest a GitHub repository into RepoPilot.")
    parser.add_argument("--url", required=True, help="GitHub repository URL")
    parser.add_argument("--branch", default="main", help="Branch to clone (default: main)")
    args = parser.parse_args()

    print(f"🚀 Initializing database connection...")
    await init_db()

    print(f"📦 Registering repository: {args.url} (branch: {args.branch})")
    async with async_session_factory() as db:
        req = RepoIngestRequest(url=args.url, branch=args.branch)
        repo = await RepositoryService.create_repository(db, req)
        repo_id = str(repo.id)
        print(f"✅ Repository record created (ID: {repo_id})")

    print("⚡ Starting background ingestion pipeline...")
    worker = IngestionWorker()
    await worker.run_ingestion(repo_id)

    async with async_session_factory() as db:
        final_repo = await RepositoryService.get_repository(db, repo.id)
        if final_repo and final_repo.status == "ready":
            print(f"🎉 Ingestion complete!")
            print(f"   Files indexed:  {final_repo.file_count}")
            print(f"   Chunks created: {final_repo.chunk_count}")
            print(f"   Languages:      {final_repo.language_stats}")
        else:
            print(f"❌ Ingestion failed: {final_repo.error_message if final_repo else 'Unknown'}")


if __name__ == "__main__":
    asyncio.run(main())

