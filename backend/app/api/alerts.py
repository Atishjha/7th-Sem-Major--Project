from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertOut
from app.security.dependencies import get_current_user
from app.utils.ids import parse_severity
router = APIRouter(tags=["alerts"])
@router.get("/alerts",response_model=list[AlertOut])
def list_alerts(
    Limit: int = Query(50,ge=1,Le=200),
    rule_key: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
)-> list[Alert]:
    stmt = select(Alert).order_by(Alert.detected_at.desc())
    if rule_key:
        stmt = stmt.where(Alert.rule_key == rule_key)
    if severity:
        stmt = stmt.where(Alert.severity == parse_severity(severity))
    stmt = stmt.limit(limit)
    return list(db.scalars(stmt))
