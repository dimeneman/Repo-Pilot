"""
Standalone background worker process and CLI job runner for RepoPilot.

Can be run as:
1. Continuous background daemon:
   python -m app.worker [daemon]
2. Single-job runner (e.g. for GitHub Actions runner):
   python -m app.worker run-job --job-id <UUID> [--access-token <TOKEN>]
3. Failure reporter (e.g. for GitHub Actions failure trap):
   python -m app.worker fail-job --job-id <UUID> --error "message"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import async_session_factory, init_db
from app.models.job import Job
from app.models.repository import Repository
from app.retrieval.vector_store import VectorStoreService
from app.workers.ingestion_worker import IngestionWorker
from app.workers.queue import default_queue

logger = get_logger("worker")


class WorkerRunner:
    """Manages the lifecycle and job processing loop for the background worker daemon."""

    def __init__(self):
        self.running = True
        self.worker = IngestionWorker()
        self.queue = default_queue

    def stop(self, *args):
        """Signal handler to initiate clean shutdown."""
        logger.info("Received termination signal, initiating graceful worker shutdown...")
        self.running = False

    async def run(self):
        """Main worker execution loop."""
        logger.info("Starting RepoPilot Ingestion Worker daemon...")

        # Ensure database tables and collection are initialized
        try:
            await init_db()
        except Exception as exc:
            logger.warning(f"Worker init_db notice: {exc}")

        try:
            vs = VectorStoreService()
            await vs.ensure_collection()
        except Exception as exc:
            logger.warning(f"Worker ensure_collection notice: {exc}")

        # Reconcile any orphaned jobs from previous crashes
        await self.worker.reconcile_stale_jobs()

        logger.info("Ingestion Worker ready — actively listening for jobs...")

        while self.running:
            try:
                # Dequeue next job (Redis or PostgreSQL polling)
                job_data = await self.queue.dequeue_job(timeout=int(settings.WORKER_POLL_INTERVAL))
                if job_data:
                    job_id = job_data["job_id"]
                    access_token = job_data.get("access_token")
                    logger.info(f"Worker picked up job {job_id}")
                    await self.worker.process_job(job_id=job_id, access_token=access_token)
                else:
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                logger.info("Worker task cancelled.")
                break
            except Exception as exc:
                logger.exception(f"Unexpected error in worker loop: {exc}")
                await asyncio.sleep(settings.WORKER_POLL_INTERVAL)

        logger.info("RepoPilot Ingestion Worker stopped cleanly.")


async def run_worker_loop():
    """Run worker loop directly inside an existing event loop (e.g. for embedded mode)."""
    runner = WorkerRunner()
    await runner.run()


async def execute_single_job(job_id: str, access_token: Optional[str] = None) -> bool:
    """Execute a single ingestion job to completion (used by GitHub Actions or CLI)."""
    logger.info(f"Starting execution of single ingestion job {job_id}...")
    try:
        await init_db()
    except Exception as exc:
        logger.warning(f"Job runner init_db notice: {exc}")

    try:
        vs = VectorStoreService()
        await vs.ensure_collection()
    except Exception as exc:
        logger.warning(f"Job runner ensure_collection notice: {exc}")

    worker = IngestionWorker()
    await worker.process_job(job_id=job_id, access_token=access_token)

    # Verify outcome in database
    async with async_session_factory() as db:
        job = await db.get(Job, uuid.UUID(str(job_id)))
        if job and job.status == "completed":
            logger.info(f"Job {job_id} completed successfully.")
            return True
        err = job.error_message if job else "Job record not found"
        logger.error(f"Job {job_id} ended with status '{job.status if job else 'unknown'}': {err}")
        return False


async def execute_fail_job(
    job_id: str,
    error_message: str,
    db_session: Optional[Any] = None,
) -> None:
    """Mark a job and repository as failed on external runner crash or timeout."""
    logger.warning(f"Marking job {job_id} as failed: {error_message}")

    async def _apply_failure(db):
        target_id = uuid.UUID(str(job_id))
        job = await db.get(Job, target_id)
        if job:
            now = datetime.now(timezone.utc)
            job.status = "failed"
            job.stage = "failed"
            job.error_message = error_message
            job.completed_at = now
            job.updated_at = now
            repo = await db.get(Repository, job.repo_id)
            if repo:
                repo.status = "failed"
                repo.error_message = error_message
                repo.updated_at = now
            await db.commit()
            logger.info(f"Durable failure status recorded for job {job_id}.")

    if db_session is not None:
        await _apply_failure(db_session)
    else:
        async with async_session_factory() as db:
            await _apply_failure(db)


def main():
    """CLI entry point for the worker process supporting daemon and single-job modes."""
    parser = argparse.ArgumentParser(description="RepoPilot Worker & Ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # Daemon mode (default)
    subparsers.add_parser("daemon", help="Run background daemon polling for jobs (default)")

    # Run single job
    run_parser = subparsers.add_parser("run-job", help="Run a specific job by ID to completion")
    run_parser.add_argument("--job-id", required=True, help="UUID of the job to process")
    run_parser.add_argument("--access-token", default=None, help="GitHub access token for private repo")

    # Fail single job
    fail_parser = subparsers.add_parser("fail-job", help="Mark a job as failed on runner crash")
    fail_parser.add_argument("--job-id", required=True, help="UUID of the job to mark failed")
    fail_parser.add_argument("--error", default="Job execution failed", help="Error message")

    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if args.command == "run-job":
        try:
            success = loop.run_until_complete(
                execute_single_job(args.job_id, access_token=args.access_token)
            )
            sys.exit(0 if success else 1)
        finally:
            loop.close()
    elif args.command == "fail-job":
        try:
            loop.run_until_complete(execute_fail_job(args.job_id, args.error))
            sys.exit(0)
        finally:
            loop.close()
    else:
        # Default daemon mode
        runner = WorkerRunner()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, runner.stop)
            except (NotImplementedError, RuntimeError):
                pass
        try:
            loop.run_until_complete(runner.run())
        finally:
            loop.close()


if __name__ == "__main__":
    main()
