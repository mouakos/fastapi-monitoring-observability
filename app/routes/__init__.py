"""Route package — aggregates all sub-routers."""

from fastapi import APIRouter

from app.routes.errors import router as errors_router
from app.routes.monotoring import router as monitoring_router

router = APIRouter()
router.include_router(monitoring_router)
router.include_router(errors_router)

__all__ = ["router"]
