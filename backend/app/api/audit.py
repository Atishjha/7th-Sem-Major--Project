from fastapi import APIRouter,Depends,Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogOut
from app.security.dependencies import get_current_user
router = APIRouter(prefix="/audit",tags=["audit"])
@router.get("",response_model=list[AuditLogOut])
def list_audit_logs(
    limit: int = Query(100,ge=1,le=500),
    reesource_type: str|None = None,
    resource_id: str|None = None,
    username: str|None = None,
    db: Session = Depends(get_db),
    _:User = Depends(get_current_user),
) -> list[AuditLog]:
    """Read-only for every role — accountability/transparency, same
    pattern as the MITRE coverage view, not a configurable surface."""
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if reesource_type:
        stmt = stmt.where(AuditLog.resource_type == reesource_type)
    if resource_id:
        stmt = stmt.where(AuditLog.resource_id == resource_id)
    if username:
        stmt = stmt.where(AuditLog.username == username)
    return list(db.scalars(stmt.limit(limit)))