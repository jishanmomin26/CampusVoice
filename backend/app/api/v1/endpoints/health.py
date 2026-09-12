"""Health check endpoint router."""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get(
    "/health",
    summary="Service Health Check",
    description="Returns the current operational status of the CampusVoice API.",
    tags=["Health"],
)
async def health_check():
    """Returns simple JSON indicating API health."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
