"""
log_action is called at the end of every require_role-gated route
that changes state — that's the whole audit scope for this phase:
every privileged mutation, nothing more, nothing less. A reader can
verify the scope is complete by grepping for every `require_role(...)`
call site in app/api/ and checking each one's route body calls this.
"""
from typing import Any
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
def log_action(
    db:Session,
    *,
    username:str,action:str,resource_type:str,
    resource_id:str|None=None,
    old_value:dict[str,Any]|None=None,
    new_value:dict[str,Any]|None=None,
    result:str="SUCCESS",
)-> AuditLog:
    entry=AuditLog(
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_value=old_value,
        new_value=new_value,
        result=result,
    )
    db.add(entry)
    db.commit()
    return entry