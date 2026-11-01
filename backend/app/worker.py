"""
Standalone background worker process for RepoPilot.

Continuously pulls and executes ingestion and reindexing jobs outside
the web request lifecycle. Suitable for Docker Compose and Render background workers.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import init_db
from app.retrieval.vector_store import VectorStoreService
from app.workers.ingestion_worker import IngestionWorker
from app.workers.queue import default_queue

logger = get_logger("worker")


class WorkerRunner:
    """Manages the lifecycle and job processing loop for the background worker."""

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


def main():
    """CLI entry point for the worker process."""
    runner = WorkerRunner()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, runner.stop)
        except (NotImplementedError, RuntimeError):
            # Signals might not be supported in all environments (e.g. non-main thread)
            pass

    try:
        loop.run_until_complete(runner.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
