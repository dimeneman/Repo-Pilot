#!/usr/bin/env python3
"""
CLI script to rebuild the vector index for a repository.

Usage:
    python scripts/rebuild_index.py --repo-id <UUID>
    python scripts/rebuild_index.py --all
"""
import argparse
import asyncio
import sys
import uuid
from pathlib import Path
from sqlalchemy import select

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.db.session import async_session_factory, init_db
from app.models.repository import Repository
from app.workers.ingestion_worker import IngestionWorker


async def rebuild_one(repo_id: uuid.UUID):
    print(f"🔄 Rebuilding index for repository {repo_id}...")
    worker = IngestionWorker()
    await worker.run_ingestion(str(repo_id))
    print(f"✅ Rebuild finished for {repo_id}")


async def main():
    parser = argparse.ArgumentParser(description="Rebuild vector indexes in RepoPilot.")
    parser.add_argument("--repo-id", help="UUID of repository to rebuild")
    parser.add_argument("--all", action="store_true", help="Rebuild all repositories")
    args = parser.parse_args()

    if not args.repo_id and not args.all:
        print("Please specify --repo-id <UUID> or --all")
        sys.exit(1)

    await init_db()

    async with async_session_factory() as db:
        if args.repo_id:
            await rebuild_one(uuid.UUID(args.repo_id))
        elif args.all:
            repos = (await db.execute(select(Repository))).scalars().all()
            print(f"Found {len(repos)} repositories to rebuild.")
            for r in repos:
                await rebuild_one(r.id)


if __name__ == "__main__":
    asyncio.run(main())

