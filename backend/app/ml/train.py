"""
Training pipeline: Dataset -> Cleaning -> Feature Engineering ->
Scaling -> Isolation Forest -> Anomaly Score -> Anomaly Classification.

Honesty rules from the spec, followed exactly:
- Never invent accuracy. This dataset has no ground-truth labels, so
  `accuracy_status` is always "not_applicable" — never a fabricated
  precision/recall/F1.
- Every number in the returned MLTrainingRun (num_samples,
  num_features, timestamp, contamination, anomalies_flagged) comes
  from the actual fitted model and actual data, not a placeholder.
"""

from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.ml.features import FEATURE_COLUMNS, build_feature_matrix
from app.models.ml_prediction import MLPrediction
from app.models.ml_training_run import MLTrainingRun

# backend/app/ml/train.py -> parents[3] is the project root, where the
# spec's top-level ml/ directory lives (sibling to backend/ and frontend/).
MODEL_DIR = Path(__file__).resolve().parents[3] / "ml" / "models"

MIN_SAMPLES_TO_TRAIN = 5


class NotEnoughDataError(ValueError):
    pass


def train_and_score(
    db: Session, contamination: float = 0.05, window_minutes: int = 5
) -> MLTrainingRun:
    df = build_feature_matrix(db, window_minutes=window_minutes)

    if len(df) < MIN_SAMPLES_TO_TRAIN:
        raise NotEnoughDataError(
            f"Only {len(df)} feature window(s) available; need at least "
            f"{MIN_SAMPLES_TO_TRAIN}. Run a scenario or two from Demo Mode "
            "first, or seed baseline events."
        )

    X = df[FEATURE_COLUMNS].to_numpy(dtype=float)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200, contamination=contamination, random_state=42
    )
    model.fit(X_scaled)

    raw_scores = model.decision_function(X_scaled)  # higher = more normal
    predictions = model.predict(X_scaled)  # -1 = anomalous, 1 = normal

    # Normalize to 0..1 where 1 = most anomalous, for the "Anomaly Score:
    # 0.91" style display the spec shows as an example.
    inverted = -raw_scores
    score_range = inverted.max() - inverted.min()
    if score_range > 0:
        normalized_scores = (inverted - inverted.min()) / score_range
    else:
        normalized_scores = np.zeros_like(inverted)

    is_anomalous = predictions == -1
    anomalies_flagged = int(is_anomalous.sum())

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    trained_at = datetime.now(timezone.utc)
    model_version = f"isolation_forest_{trained_at.strftime('%Y%m%d_%H%M%S')}"
    file_path = MODEL_DIR / f"{model_version}.joblib"
    joblib.dump({"model": model, "scaler": scaler, "features": FEATURE_COLUMNS}, file_path)

    training_run = MLTrainingRun(
        model_type="IsolationForest",
        model_version=model_version,
        training_dataset=(
            f"Synthetic event stream ({window_minutes}-minute windows per source IP)"
        ),
        num_samples=len(df),
        num_features=len(FEATURE_COLUMNS),
        feature_names=FEATURE_COLUMNS,
        contamination=contamination,
        accuracy_status="not_applicable",
        evaluation={
            "note": (
                "Unsupervised model — this dataset has no labeled "
                "attack/normal ground truth, so accuracy/precision/recall "
                "are not computed. Classification uses the model's own "
                "contamination-based decision boundary."
            )
        },
        anomalies_flagged=anomalies_flagged,
        file_path=str(file_path.relative_to(MODEL_DIR.parents[1])),
        trained_at=trained_at,
    )
    db.add(training_run)
    db.flush()  # get training_run.id for the FK below

    for i, row in df.iterrows():
        db.add(
            MLPrediction(
                training_run_id=training_run.id,
                source_ip=row["source_ip"],
                window_start=row["window_start"],
                features={col: float(row[col]) for col in FEATURE_COLUMNS},
                anomaly_score=float(normalized_scores[i]),
                is_anomalous=bool(is_anomalous[i]),
            )
        )

    db.commit()
    db.refresh(training_run)
    return training_run
