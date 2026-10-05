from datetime import datetime
from pydantic import BaseModel
from app.models.response_action import ActionStatus, ActionType
class ResponseActionOut(BaseModel):
    id: int
    response_id: str
    incident_id: int
    action_type: ActionType
    action_label: str
    target: str
    recommended_reason: str
    status: ActionStatus
    result_message: str | None
    decided_by_username: str | None
    decided_at: datetime | None
    created_at: datetime
    class Config:
        from_attributes = True
