"""System health endpoints
Used by Docker Compose healthchecks and by the "System Health" page
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from app.config import settings
router = APIRouter(tags=["system"])
@router.get("/health")
def health_check() -> dict:
    return{
        "status":"ok",
        "service":settings.APP_NAME,
        "environment":settings.ENVIRONMENT,
        "time":datetime.now(timezone.utc).isoformat(),
    }