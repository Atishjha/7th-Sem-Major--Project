from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.ml.train import NotEnoughDataError, train_and_score
from app.models.ml_prediction import MLPrediction
from app.models.ml_training_run import MLTrainingRun
from app.models.user import User, UserRole
from app.schemas.ml import MLPredictionOut, MLStatusOut, MLTrainingRunOut, TrainRequest
from app.security.dependencies import get_current_user, require_role
router = APIRouter(prefix="/ml", tags=["ml"])
can_train_model = require_role(UserRole.ADMIN, UserRole.SOC_ANALYST)
@router.get("/status", response_model=MLStatusOut)
def ml_status(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> MLStatusOut:
    latest = db.scalar(
        select(MLTrainingRun).order_by(MLTrainingRun.trained_at.desc()).limit(1)
    )
    return MLStatusOut(has_model=latest is not None, latest_run=latest)
@router.post("/train", response_model=MLTrainingRunOut)
def train_model(
    payload: TrainRequest,
    db: Session = Depends(get_db),
    _: User = Depends(can_train_model),
) -> MLTrainingRun:
    try:
        return train_and_score(
            db, contamination=payload.contamination, window_minutes=payload.window_minutes
        )
    except NotEnoughDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
@router.get("/predictions", response_model=list[MLPredictionOut])
def list_predictions(
    limit: int = 100,
    anomalous_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MLPrediction]:
    latest_run_id = db.scalar(
        select(MLTrainingRun.id).order_by(MLTrainingRun.trained_at.desc()).limit(1)
    )
    if latest_run_id is None:
        return []
    stmt = (
        select(MLPrediction)
        .where(MLPrediction.training_run_id == latest_run_id)
        .order_by(MLPrediction.anomaly_score.desc())
        .limit(limit)
    )
    if anomalous_only:
        stmt = stmt.where(MLPrediction.is_anomalous.is_(True))
    return list(db.scalars(stmt))
