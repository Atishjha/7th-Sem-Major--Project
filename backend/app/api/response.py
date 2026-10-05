from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.response_action import ActionStatus, ResponseAction
from app.models.user import User, UserRole
from app.schemas.response import ResponseActionOut
from app.security.dependencies import get_current_user, require_role
from app.services.response_center import approve_action, reject_action, serialize_action
router = APIRouter(prefix="/response", tags=["response"])
can_decide = require_role(UserRole.ADMIN, UserRole.SOC_ANALYST)
def _load_or_404(db: Session, response_id: str) -> ResponseAction:
    action = db.scalar(select(ResponseAction).where(ResponseAction.response_id == response_id))
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No response action '{response_id}'")
    return action
@router.get("", response_model=list[ResponseActionOut])
def list_response_actions(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ResponseActionOut]:
    """Global Response Center queue — every recommended/decided action
    across all incidents, read-only for every role."""
    stmt = select(ResponseAction).order_by(ResponseAction.created_at.desc())
    if status_filter:
        try:
            stmt = stmt.where(ResponseAction.status == ActionStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status_filter}'")
    return [serialize_action(a) for a in db.scalars(stmt)]
@router.post("/{response_id}/approve", response_model=ResponseActionOut)
def approve(
    response_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(can_decide),
) -> ResponseActionOut:
    action = _load_or_404(db, response_id)
    if action.status != ActionStatus.RECOMMENDED:
        raise HTTPException(status_code=409, detail=f"Action is already '{action.status.value}'")
    return serialize_action(approve_action(db, action, user))
@router.post("/{response_id}/reject", response_model=ResponseActionOut)
def reject(
    response_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(can_decide),
) -> ResponseActionOut:
    action = _load_or_404(db, response_id)
    if action.status != ActionStatus.RECOMMENDED:
        raise HTTPException(status_code=409, detail=f"Action is already '{action.status.value}'")
    return serialize_action(reject_action(db, action, user))
