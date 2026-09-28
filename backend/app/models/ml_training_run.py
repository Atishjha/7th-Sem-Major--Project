"""
One row per Isolation Forest training run. This is what the /ml page
displays: model type, dataset description, sample/feature counts,
training timestamp, contamination (anomaly threshold), and evaluation
status.

`accuracy_status` is always "not_applicable" here: this project has no
labeled attack/normal dataset, so per the spec we never invent an
accuracy number — an unsupervised model with no ground truth reports
"Not Applicable", not a fabricated metric.
"""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, DateTime, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
class MLTrainingRun(Base):
    __tablename__ = "ml_training_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_type: Mapped[str] = mapped_column(String(64), default="IsolationForest")
    model_version: Mapped[str] = mapped_column(String(64), unique=True)
    training_dataset: Mapped[str] = mapped_column(String(255))

    num_samples: Mapped[int] = mapped_column(Integer)
    num_features: Mapped[int] = mapped_column(Integer)
    feature_names: Mapped[list[str]] = mapped_column(JSON)
    contamination: Mapped[float] = mapped_column(Float)

    accuracy_status: Mapped[str] = mapped_column(String(32), default="not_applicable")
    evaluation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    anomalies_flagged: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str] = mapped_column(String(255))

    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
