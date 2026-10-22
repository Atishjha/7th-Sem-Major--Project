from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.ml.dataset import (
    DatasetError,
    list_processed_files,
    list_raw_files,
    preprocess_dataset,
    save_uploaded_file,
    train_on_dataset,
)
from app.models.ml_training_run import MLTrainingRun
from app.models.user import User, UserRole
from app.schemas.dataset import DatasetFilesOut, PreprocessRequest, PreprocessResultOut, TrainDatasetRequest
from app.schemas.ml import MLTrainingRunOut
from app.security.dependencies import get_current_user, require_role
from app.services.audit import log_action

router = APIRouter(prefix="/dataset", tags=["dataset"])

can_manage_dataset = require_role(UserRole.ADMIN, UserRole.SOC_ANALYST)


@router.get("/files", response_model=DatasetFilesOut)
def get_files(_: User = Depends(get_current_user)) -> DatasetFilesOut:
    """Shows both files uploaded via the API and any a developer placed
    directly into data/raw/ / data/processed/ — plain directory listing,
    no hidden state."""
    return DatasetFilesOut(raw=list_raw_files(), processed=list_processed_files())


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(can_manage_dataset),
) -> dict:
    content = await file.read()
    try:
        info = save_uploaded_file(file.filename, content)
    except DatasetError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    log_action(
        db, username=user.username, action=f"Uploaded dataset '{file.filename}'",
        resource_type="dataset", resource_id=file.filename,
        new_value={"size_bytes": info["size_bytes"]},
    )
    return info


@router.post("/preprocess", response_model=PreprocessResultOut)
def preprocess(
    payload: PreprocessRequest,
    db: Session = Depends(get_db),
    user: User = Depends(can_manage_dataset),
) -> PreprocessResultOut:
    try:
        result = preprocess_dataset(payload.raw_filename, payload.label_column)
    except DatasetError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    log_action(
        db, username=user.username, action=f"Preprocessed dataset '{payload.raw_filename}'",
        resource_type="dataset", resource_id=payload.raw_filename,
        new_value={"num_records": result["num_records"], "num_features": result["num_features"]},
    )
    return PreprocessResultOut(**result)


@router.post("/train", response_model=MLTrainingRunOut)
def train(
    payload: TrainDatasetRequest,
    db: Session = Depends(get_db),
    user: User = Depends(can_manage_dataset),
) -> MLTrainingRun:
    try:
        run = train_on_dataset(
            db, payload.processed_filename, payload.label_column,
            payload.attack_label_values, payload.contamination,
        )
    except DatasetError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    log_action(
        db, username=user.username, action=f"Trained ML model on dataset '{payload.processed_filename}'",
        resource_type="dataset", resource_id=payload.processed_filename,
        new_value={"model_version": run.model_version, "accuracy_status": run.accuracy_status,
                   "evaluation": run.evaluation},
    )
    return run


@router.get("/runs", response_model=list[MLTrainingRunOut])
def list_dataset_runs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MLTrainingRun]:
    return list(
        db.scalars(
            select(MLTrainingRun)
            .where(MLTrainingRun.source == "uploaded_dataset")
            .order_by(MLTrainingRun.trained_at.desc())
        )
    )
