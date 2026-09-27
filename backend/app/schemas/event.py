import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.common import Severity


class EventOut(BaseModel):
    id: int
    event_id: str
    timestamp: datetime
    source: str
    source_ip: str | None
    destination_ip: str | None
    username: str | None
    hostname: str | None
    event_type: str
    action: str
    status: str
    severity: Severity
    message: str
    event_metadata: dict[str, Any]

    class Config:
        from_attributes = True


class ScenarioName(str, enum.Enum):
    BRUTE_FORCE = "brute_force"
    POWERSHELL = "powershell"
    DNS_ANOMALY = "dns_anomaly"
    NETWORK_ANOMALY = "network_anomaly"
    MULTI_STAGE = "multi_stage"


class SimulatorStartRequest(BaseModel):
    scenario: ScenarioName


class SimulatorStatus(BaseModel):
    running: bool
    scenario: ScenarioName | None
    events_emitted: int
    total_events: int | None
    started_at: datetime | None
