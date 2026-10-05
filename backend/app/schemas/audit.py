from datetime import datetime
from typing import Any
from pydantic import BaseModel
class AuditLogOut(BaseModel):
    id:int
    timestamp:datetime
    username:str
    action:str
    resource_type:str
    resource_id:str|None
    old_value:dict[str,Any]|None
    new_value:dict[str,Any]|None
    result:str
    class Config:
        from_attributes=True