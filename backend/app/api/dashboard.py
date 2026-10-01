from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.security.dependencies import get_current_user
from app.services.dashboard_service import build_dashboard_snapshot
router = APIRouter(tags=["dashboard"])
@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DashboardResponse:
    return build_dashboard_snapshot(db)