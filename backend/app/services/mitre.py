from datetime import datetime

from pydantic import BaseModel


class TechniqueObservationOut(BaseModel):
    tactic: str
    technique_id: str
    technique_name: str
    confidence: str
    evidence_rule: str
    alert_count: int
    incident_count: int
    first_seen: datetime | None
    last_seen: datetime | None
    evidence_alert_ids: list[str]
    evidence_incident_ids: list[str]
