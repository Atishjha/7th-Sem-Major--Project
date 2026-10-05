from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.mitre import TechniqueObservationOut
from app.security.dependencies import get_current_user
from app.services.mitre_mapping import aggregate_technique_observations

router = APIRouter(prefix="/mitre", tags=["mitre"])


@router.get("/techniques", response_model=list[TechniqueObservationOut])
def list_techniques(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    """Read-only for every role, including VIEWER — this is informational
    coverage reporting, not a configurable control surface like rules."""
    return aggregate_technique_observations(db)
