"""
SQLAlchemy declarative base and model registry.

Import every model module here so that Alembic (and ``Base.metadata``)
can discover all tables.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models in RepoPilot."""

    pass


# ── Import all model modules so their tables are registered ──────────────
# These imports are intentionally side-effect-only; they attach Table
# objects to ``Base.metadata``.
import app.models.repository  # noqa: F401, E402
import app.models.file  # noqa: F401, E402
import app.models.chunk  # noqa: F401, E402
import app.models.query  # noqa: F401, E402
import app.models.job  # noqa: F401, E402
