#!/usr/bin/env python3
"""
Standalone CLI script to execute an ingestion job.

Usage:
    python scripts/run_ingestion.py --job-id <UUID> [--access-token <TOKEN>]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.worker import execute_fail_job, execute_single_job


def main():
    parser = argparse.ArgumentParser(description="Run RepoPilot Ingestion Job")
    parser.add_argument("--job-id", required=True, help="UUID of the job to execute")
    parser.add_argument("--access-token", default=None, help="GitHub access token (optional)")

    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        success = loop.run_until_complete(
            execute_single_job(args.job_id, access_token=args.access_token)
        )
        sys.exit(0 if success else 1)
    except Exception as exc:
        print(f"Error executing job {args.job_id}: {exc}", file=sys.stderr)
        try:
            loop.run_until_complete(execute_fail_job(args.job_id, str(exc)))
        except Exception:
            pass
        sys.exit(1)
    finally:
        loop.close()


if __name__ == "__main__":
    main()

