"""
One row per (source_ip, time-window) feature vector scored by a
training run. `anomaly_score` is a normalized 0-1 value (1 = most
anomalous) for display; `is_anomalous` is the model's own
contamination-threshold classification via IsolationForest.predict.
"""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, DateTime, Float, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_run_id: Mapped[int] = mapped_column(ForeignKey("ml_training_runs.id"), index=True)

    source_ip: Mapped[str] = mapped_column(String(64), index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    features: Mapped[dict[str, Any]] = mapped_column(JSON)
    anomaly_score: Mapped[float] = mapped_column(Float, index=True)
    is_anomalous: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
