from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.ml.train import NotEnoughDataError, train_and_score
from app.models.ml_prediction import MLPrediction
from app.models.ml_training_run import EVENT_STREAM_SOURCE, MLTrainingRun
from app.models.user import User, UserRole
from app.schemas.ml import MLPredictionOut, MLStatusOut, MLTrainingRunOut, TrainRequest
from app.security.dependencies import get_current_user, require_role
from app.services.audit import log_action
from app.services.risk_engine import recompute_all_incidents

router = APIRouter(prefix="/ml", tags=["ml"])

can_train_model = require_role(UserRole.ADMIN, UserRole.SOC_ANALYST)


@router.get("/status", response_model=MLStatusOut)
def ml_status(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> MLStatusOut:
    latest = db.scalar(
        select(MLTrainingRun)
        .where(MLTrainingRun.source == EVENT_STREAM_SOURCE)
        .order_by(MLTrainingRun.trained_at.desc())
        .limit(1)
    )
    return MLStatusOut(has_model=latest is not None, latest_run=latest)


@router.post("/train", response_model=MLTrainingRunOut)
def train_model(
    payload: TrainRequest,
    db: Session = Depends(get_db),
    user: User = Depends(can_train_model),
) -> MLTrainingRun:
    try:
        run = train_and_score(
            db, contamination=payload.contamination, window_minutes=payload.window_minutes
        )
    except NotEnoughDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # An incident's risk score includes an ML factor that is looked up in the
    # latest model. Incidents scored before this model existed would otherwise
    # keep a stale 0 for it, so re-score them now.
    rescored = recompute_all_incidents(db)
    log_action(
        db, username=user.username, action="Trained ML anomaly model on the event stream",
        resource_type="ml_model", resource_id=run.model_version,
        new_value={
            "model_version": run.model_version, "num_samples": run.num_samples,
            "anomalies_flagged": run.anomalies_flagged, "contamination": run.contamination,
            "window_minutes": payload.window_minutes, "incidents_rescored": rescored,
        },
    )
    return run


@router.get("/predictions", response_model=list[MLPredictionOut])
def list_predictions(
    limit: int = 100,
    anomalous_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MLPrediction]:
    latest_run_id = db.scalar(
        select(MLTrainingRun.id)
        .where(MLTrainingRun.source == EVENT_STREAM_SOURCE)
        .order_by(MLTrainingRun.trained_at.desc())
        .limit(1)
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
