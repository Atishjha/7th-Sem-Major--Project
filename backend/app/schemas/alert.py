from datetime import datetime
from typing import Any
from pydantic import BaseModel
from app.models.common import Severity
class AlertOut(BaseModel):
    id: int
    alert_id: str
    rule_key: str
    rule_name: str
    title: str
    severity: Severity
    status: str
    username: str | None
    source_ip: str | None
    hostname: str | None
    triggering_event_ids: list[int]
    alert_metadata: dict[str, Any]
    detected_at: datetime
    class Config:
        from_attributes = True

class DetectionRuleOut(BaseModel):
    id: int
    rule_key: str
    name: str
    description: str
    enabled: bool
    config: dict[str, Any]
    updated_at: datetime
    class Config:
        from_attributes = True
class DetectionRuleUpdate(BaseModel):
    rule_key: str
    enabled: bool | None = None
    config: dict[str, Any] | None = None
