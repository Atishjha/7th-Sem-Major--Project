from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.asset import Asset
from app.models.user import User
from app.schemas.asset import AssetOut
from app.security.dependencies import get_current_user
router = APIRouter(prefix="/assets", tags=["assets"])
@router.get("", response_model=list[AssetOut])
def list_assets(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AssetOut]:
    """Read-only for now (no page consumes editing yet — see README).
    Registering a hostname here is what gives it a real Asset
    Criticality factor in the Risk Engine instead of the default tier."""
    return [AssetOut.model_validate(asset) for asset in db.scalars(select(Asset).order_by(Asset.hostname))]
