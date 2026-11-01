"""
API router aggregator — includes every sub-router with its prefix.
"""

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.repos import router as repos_router
from app.api.routes.sources import router as sources_router

router = APIRouter()

router.include_router(health_router, tags=["Health"])
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(repos_router, prefix="/repos", tags=["Repositories"])
router.include_router(chat_router, prefix="/chat", tags=["Chat"])
router.include_router(sources_router, prefix="/sources", tags=["Sources"])

api_router = router
__all__ = ["router", "api_router"]

