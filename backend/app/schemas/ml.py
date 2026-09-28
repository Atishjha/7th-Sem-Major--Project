from datetime import datetime
from typing import Any
from pydantic import BaseModel
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
    contamination: float = 0.05
    window_minutes: int = 5
class MLStatusOut(BaseModel):
    has_model: bool
    latest_run: MLTrainingRunOut | None
