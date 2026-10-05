from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.ai.context_builder import build_context
from app.ai.factory import run_investigation
from app.services.mitre_mapping import techniques_for_rules
from app.services.response_center import create_recommended_actions, serialize_action
from app.services.audit import log_action
from app.models.alert import Alert
from app.models.ai_investigation import AIInvestigation
from app.models.event import Event
from app.models.incident import Incident, IncidentEvent
from app.models.response_action import ResponseAction
from app.models.user import User, UserRole
from app.schemas.alert import AlertOut
from app.schemas.event import EventOut
from app.schemas.ai_investigation import InvestigationOut, MitreTechniqueOut
from app.schemas.response import ResponseActionOut
from app.schemas.incident import IncidentDetailOut, IncidentOut
from app.security.dependencies import get_current_user, require_role
from app.utils.ids import parse_severity

can_investigate = require_role(UserRole.ADMIN, UserRole.SOC_ANALYST)

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
    events = list(
        db.scalars(
            select(Event)
            .join(IncidentEvent, IncidentEvent.event_id == Event.id)
            .where(IncidentEvent.incident_id == incident.id)
            .order_by(Event.timestamp)
        )
    )
    base = IncidentOut.model_validate(incident).model_dump()
    return IncidentDetailOut(
        **base,
        alerts=[AlertOut.model_validate(a) for a in alerts],
        events=[EventOut.model_validate(e) for e in events],
    )


def _load_incident_or_404(db: Session, incident_id: str) -> Incident:
    incident = db.scalar(select(Incident).where(Incident.incident_id == incident_id))
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No incident '{incident_id}'"
        )
    return incident


@router.post("/{incident_id}/investigate", response_model=InvestigationOut)
async def investigate_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(can_investigate),
) -> InvestigationOut:
    incident = _load_incident_or_404(db, incident_id)
    alerts = list(
        db.scalars(select(Alert).where(Alert.incident_id == incident.id).order_by(Alert.detected_at))
    )
    context = build_context(db, incident, alerts)
    result, provider_used = await run_investigation(context)

    db.add(
        AIInvestigation(
            incident_id=incident.id,
            provider_used=provider_used,
            investigation=result.model_dump(mode="json"),
        )
    )
    db.commit()

    log_action(
        db, username=user.username, action="Ran AI investigation",
        resource_type="incident", resource_id=incident.incident_id,
        new_value={"provider_used": provider_used},
    )
    return result


@router.get("/{incident_id}/investigation", response_model=InvestigationOut | None)
def get_latest_investigation(
    incident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> InvestigationOut | None:
    incident = _load_incident_or_404(db, incident_id)
    latest = db.scalar(
        select(AIInvestigation)
        .where(AIInvestigation.incident_id == incident.id)
        .order_by(AIInvestigation.created_at.desc())
        .limit(1)
    )
    return InvestigationOut(**latest.investigation) if latest else None


@router.get("/{incident_id}/mitre", response_model=list[MitreTechniqueOut])
def get_incident_mitre(
    incident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MitreTechniqueOut]:
    """This incident's own MITRE mapping — doesn't require running an AI
    investigation first; derived directly from the rules its alerts
    triggered, same shared mapping the AI analyst's output uses."""
    incident = _load_incident_or_404(db, incident_id)
    rule_keys = (incident.incident_metadata or {}).get("rule_keys", [])
    return [MitreTechniqueOut(**t) for t in techniques_for_rules(db, rule_keys)]


@router.get("/{incident_id}/response", response_model=list[ResponseActionOut])
def get_incident_response_actions(
    incident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ResponseActionOut]:
    """Auto-recommends (idempotently) on first open, then always returns
    this incident's full action history — recommended, approved, and
    rejected alike."""
    incident = _load_incident_or_404(db, incident_id)
    create_recommended_actions(db, incident)
    actions = list(
        db.scalars(
            select(ResponseAction)
            .where(ResponseAction.incident_id == incident.id)
            .order_by(ResponseAction.created_at)
        )
    )
    return [serialize_action(a) for a in actions]
