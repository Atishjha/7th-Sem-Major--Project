from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.alert import Alert
from app.models.incident import Incident, IncidentEvent
from app.models.user import User
from app.schemas.alert import AlertOut
from app.schemas.incident import IncidentDetailOut, IncidentOut
from app.security.dependencies import get_current_user
from app.utils.ids import parse_severity

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    limit: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    severity: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Incident]:
    stmt = select(Incident).order_by(Incident.last_seen.desc())
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)
    if severity:
        stmt = stmt.where(Incident.severity == parse_severity(severity))
    return list(db.scalars(stmt.limit(limit)))


@router.get("/{incident_id}", response_model=IncidentDetailOut)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> IncidentDetailOut:
    incident = db.scalar(select(Incident).where(Incident.incident_id == incident_id))
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No incident '{incident_id}'",
        )
    alerts = list(
        db.scalars(
            select(Alert).where(Alert.incident_id == incident.id).order_by(Alert.detected_at)
        )
    )
    event_ids = list(
        db.scalars(
            select(IncidentEvent.event_id)
            .where(IncidentEvent.incident_id == incident.id)
            .order_by(IncidentEvent.event_id)
        )
    )
    base = IncidentOut.model_validate(incident).model_dump()
    return IncidentDetailOut(
        **base,
        alerts=[AlertOut.model_validate(a) for a in alerts],
        event_ids=event_ids,
    )
