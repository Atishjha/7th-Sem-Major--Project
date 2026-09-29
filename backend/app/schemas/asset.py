from datetime import datetime
from pydantic import BaseModel
from app.models.common import Severity
class AssetOut(BaseModel):
    id: int
    hostname: str
    criticality: Severity
    description: str
    created_at: datetime
    class Config:
        from_attributes = True
