"""
FastAPI dependencies shared across route modules.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.db.session import get_db as _get_db
from app.schemas.common import PaginationParams

# ── Database session dependency ──────────────────────────────────────────
DBSession = Annotated[AsyncSession, Depends(_get_db)]


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    """Optionally extract and verify the current user from the JWT.

    If no ``Authorization`` header is present the endpoint proceeds
    unauthenticated (returns ``None``).  This keeps auth *optional* —
    individual routes can raise 401 when they truly need a user.

    Returns:
        Decoded JWT payload dict, or ``None``.
    """
    if authorization is None:
        return None

    # Expect "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return verify_token(parts[1])


CurrentUser = Annotated[Optional[dict], Depends(get_current_user)]


async def get_vector_store():
    """Return a configured Qdrant vector-store client.

    The actual ``VectorStore`` wrapper lives in ``app.services.vector_store``
    and is instantiated here so route handlers get a ready-to-use instance.
    """
    # Lazy import to avoid circular deps and keep the dependency light
    # when the services layer hasn't been created yet.
    try:
        from app.services.vector_store import VectorStore  # type: ignore[import-untyped]

        return VectorStore()
    except ImportError:
        # Services layer not yet built — return a placeholder so the app
        # can still start and serve non-vector-store endpoints.
        return None


VectorStoreDep = Annotated[object, Depends(get_vector_store)]


def pagination_params(
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Max records"),
) -> PaginationParams:
    """Parse and validate common pagination query parameters."""
    return PaginationParams(skip=skip, limit=limit)


Pagination = Annotated[PaginationParams, Depends(pagination_params)]
