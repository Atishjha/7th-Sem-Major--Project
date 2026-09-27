from fastapi import APIRouter, Depends,Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertOut
from app.security.dependencies import get_current_user
router = APIRouter(tags=["detections"])
@router.get("/detections",response_model=list[AlertOut])
def list_detections(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Alert]:
    """Each rule match produces exactly one Alert row, so a "detection"
    and an "alert" are the same record here. This endpoint exists
    because the spec's API list names it separately."""
    stmt = select(Alert).order_by(Alert.detected_at.desc()).limit(limit)
    return list(db.scalars(stmt))
