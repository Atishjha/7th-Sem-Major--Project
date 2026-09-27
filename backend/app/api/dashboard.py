from fastapi import APIRouter, Depends
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.security.dependencies import get_current_user
from app.services.dashboard_service import build_dashboard_snapshot
router = APIRouter(tags=["dashboard"])
@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(_: User = Depends(get_current_user)) -> DashboardResponse:
    return build_dashboard_snapshot()
