from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventOut
from app.security.dependencies import get_current_user
router = APIRouter(tags=["events"])
@router.get("/events", response_model=list[EventOut])
def list_events(
    limit: int = Query(50, ge=1, le=200),
    source: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Event]:
    stmt = select(Event).order_by(Event.timestamp.desc())
    if source:
        stmt = stmt.where(Event.source == source)
    if severity:
        stmt = stmt.where(Event.severity == severity)
    stmt = stmt.limit(limit)
    return list(db.scalars(stmt))
