from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.detection_rule import DetectionRule
from app.models.user import User, UserRole
from app.schemas.alert import DetectionRuleOut, DetectionRuleUpdate
from app.security.dependencies import get_current_user, require_role
router = APIRouter(prefix="/rules", tags=["rules"])
can_configure_rules = require_role(UserRole.ADMIN, UserRole.SOC_ANALYST)
@router.get("", response_model=list[DetectionRuleOut])
def list_rules(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DetectionRule]:
    return list(db.scalars(select(DetectionRule).order_by(DetectionRule.rule_key)))
@router.post("", response_model=DetectionRuleOut)
def update_rule(
    payload: DetectionRuleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(can_configure_rules),
) -> DetectionRule:
    rule = db.scalar(
        select(DetectionRule).where(DetectionRule.rule_key == payload.rule_key)
    )
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No rule with key '{payload.rule_key}'",
        )
    if payload.enabled is not None:
        rule.enabled = payload.enabled
    if payload.config is not None:
        rule.config = {**rule.config, **payload.config}
    db.commit()
    db.refresh(rule)
    return rule
