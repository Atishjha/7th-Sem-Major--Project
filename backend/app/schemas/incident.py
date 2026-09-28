from datetime import datetime
from typing import Any
from pydantic import BaseModel
from app.models.common import Severity
from app.schemas.alert import AlertOut
class IncidentOut(BaseModel):
    id: int
    incident_id: str
    title: str
    incident_type: str
    severity: Severity
    status: str
    primary_username: str | None
    primary_source_ip: str | None
    primary_hostname: str | None
    first_seen: datetime
    last_seen: datetime
    alert_count: int
    risk_score: float | None
    incident_metadata: dict[str, Any]
    created_at: datetime
    class Config:
        from_attributes = True
class IncidentDetailOut(IncidentOut):
    alerts: list[AlertOut]
    event_ids: list[int]
