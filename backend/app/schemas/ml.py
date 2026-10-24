from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MLTrainingRunOut(BaseModel):
    id: int
    model_type: str
    model_version: str
    training_dataset: str
    num_samples: int
    num_features: int
    feature_names: list[str]
    contamination: float
    accuracy_status: str
    evaluation: dict[str, Any]
    anomalies_flagged: int
    trained_at: datetime
    source: str
    dataset_filename: str | None

    class Config:
        from_attributes = True
        protected_namespaces = ()


class MLPredictionOut(BaseModel):
    id: int
    source_ip: str
    window_start: datetime
    features: dict[str, float]
    anomaly_score: float
    is_anomalous: bool

    class Config:
        from_attributes = True


class TrainRequest(BaseModel):
    # IsolationForest only accepts contamination in (0, 0.5]; window_minutes
    # is a divisor in feature engineering, so it must be >= 1. Validating here
    # turns bad input into a clean 422 instead of an unhandled 500.
    contamination: float = Field(0.05, gt=0, le=0.5)
    window_minutes: int = Field(5, ge=1, le=1440)


class MLStatusOut(BaseModel):
    has_model: bool
    latest_run: MLTrainingRunOut | None
