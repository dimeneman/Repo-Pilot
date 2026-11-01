"""
Structured logging configuration using Loguru.

Provides JSON output for production and human-readable pretty output for
development.  Every log record can carry a ``request_id`` for distributed
tracing.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from loguru import logger

from app.core.config import settings

if TYPE_CHECKING:
    from loguru import Logger

# ── Remove the default sink so we can configure our own ──────────────────
logger.remove()

# ── JSON format for production logs ──────────────────────────────────────
_JSON_FORMAT = (
    '{{"timestamp":"{time:YYYY-MM-DDTHH:mm:ss.SSS!UTC}Z",'
    '"level":"{level}",'
    '"message":"{message}",'
    '"module":"{module}",'
    '"function":"{function}",'
    '"line":{line},'
    '"request_id":"{extra[request_id]}"}}'
)

# ── Pretty format for development ────────────────────────────────────────
_PRETTY_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<blue>{extra[request_id]}</blue> | "
    "{message}"
)


def _setup_logging() -> None:
    """Configure Loguru sinks based on the current settings."""
    log_level = "DEBUG" if settings.DEBUG else "INFO"

    if settings.DEBUG:
        # Pretty coloured output to stderr
        logger.add(
            sys.stderr,
            format=_PRETTY_FORMAT,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        # Structured JSON to stdout (easy to ship to log aggregators)
        logger.add(
            sys.stdout,
            format=_JSON_FORMAT,
            level=log_level,
            serialize=False,  # we build our own JSON above
        )

    # Optional file sink – always JSON
    logger.add(
        "logs/repopilot.log",
        format=_JSON_FORMAT,
        level=log_level,
        rotation="50 MB",
        retention="14 days",
        compression="gz",
        enqueue=True,  # thread-safe writes
    )


# Run setup once on import
_setup_logging()


def get_logger(request_id: str = "-") -> "Logger":
    """Return a logger instance bound to the given *request_id*.

    Usage::

        log = get_logger(request_id="abc-123")
        log.info("Processing request")

    Args:
        request_id: A unique identifier for the current request, useful
            for correlating log entries across an async call chain.

    Returns:
        A Loguru ``Logger`` bound with the ``request_id`` extra field.
    """
    return logger.bind(request_id=request_id)
