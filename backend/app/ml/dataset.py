"""
Dataset upload, preprocessing, and training pipeline (Phase 14).

Supports CSV and Parquet, per the spec. Files placed directly into
data/raw/ by a developer (not just ones uploaded via the API) are
visible too — list_raw_files() just reads the directory.

The key difference from Phase 6's event-stream training
(app/ml/train.py): when the caller names a label column, this module
computes REAL precision/recall/F1/accuracy against it via
sklearn.metrics — never a fabricated number. With no label column,
it's honestly "Accuracy: Not Applicable", the same rule Phase 6
follows for our own unlabeled synthetic events.

Shared by two front-ends: the Dataset & ML page (app/api/dataset.py)
and the command-line tool scripts/train_model.py.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.models.ml_training_run import MLTrainingRun
from app.utils.paths import project_root

PROJECT_ROOT = project_root()
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "ml" / "models"

ALLOWED_EXTENSIONS = {".csv", ".parquet"}


class DatasetError(ValueError):
    pass


def _resolve_inside(base: Path, filename: str) -> Path:
    """Resolve `filename` under `base`, refusing anything that escapes it.

    Filenames arrive from request bodies, so '../../elsewhere.csv', absolute
    paths, subdirectories, and symlinks pointing outside are all rejected:
    the resolved file's parent must be exactly `base`.
    """
    candidate = (base / filename).resolve()
    if candidate.parent != base.resolve():
        raise DatasetError(f"Invalid filename '{filename}'.")
    return candidate


def _file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def list_raw_files() -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(
        (_file_info(p) for p in RAW_DIR.iterdir() if p.suffix in ALLOWED_EXTENSIONS),
        key=lambda f: f["filename"],
    )


def list_processed_files() -> list[dict]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(
        (_file_info(p) for p in PROCESSED_DIR.iterdir() if p.suffix in ALLOWED_EXTENSIONS),
        key=lambda f: f["filename"],
    )


def save_uploaded_file(filename: str, content: bytes) -> dict:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise DatasetError(f"Unsupported file type '{ext}'. Only .csv and .parquet are supported.")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dest = RAW_DIR / Path(filename).name
    dest.write_bytes(content)
    return _file_info(dest)


def _read(path: Path) -> pd.DataFrame:
    if path.suffix == ".csv":
        # encoding_errors="replace": some public datasets (CICIDS2017's
        # web-attack labels) contain a stray non-UTF-8 byte that would
        # otherwise abort the whole read.
        return pd.read_csv(path, encoding_errors="replace", low_memory=False)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    raise DatasetError(f"Unsupported file type '{path.suffix}'.")


def _clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise a freshly-read frame.

    Strips whitespace from column names (CICIDS2017 headers have leading
    spaces, e.g. ' Label') and turns +/-infinity into NaN, so the normal
    missing-value drop removes those rows (CICIDS2017 has 'Infinity' in its
    byte/packet-rate columns, which would otherwise crash the scaler).
    """
    df.columns = df.columns.astype(str).str.strip()
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols):
        df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
    return df


def load_raw_clean(filename: str) -> pd.DataFrame:
    path = _resolve_inside(RAW_DIR, filename)
    if not path.exists():
        raise DatasetError(
            f"No raw file named '{filename}' in {RAW_DIR}. Copy it there first "
            "(or upload it on the Dataset page)."
        )
    return _clean_frame(_read(path))


def attack_mask(
    labels: pd.Series,
    attack_values: list[str] | None = None,
    benign_values: list[str] | None = None,
) -> pd.Series:
    """True where a row is an attack. Give EITHER the attack label value(s)
    or the benign one(s) (then everything else counts as an attack — the
    convenient form for datasets with dozens of attack names)."""
    attack_set = {str(v).strip() for v in (attack_values or []) if str(v).strip()}
    benign_set = {str(v).strip() for v in (benign_values or []) if str(v).strip()}
    if attack_set and benign_set:
        raise DatasetError("Give attack label value(s) or benign label value(s), not both.")
    if not attack_set and not benign_set:
        raise DatasetError(
            "A label column was given but neither attack nor benign label values — say "
            "which value(s) mean 'attack' (or which mean 'benign') so evaluation has "
            "something to compare against."
        )
    text = labels.astype(str).str.strip()
    return text.isin(attack_set) if attack_set else ~text.isin(benign_set)


def preprocess_dataset(
    raw_filename: str,
    label_column: str | None,
    drop_columns: list[str] | None = None,
) -> dict:
    df = load_raw_clean(raw_filename)
    rows_read = len(df)

    label_column = label_column.strip() if label_column else None
    if label_column and label_column not in df.columns:
        raise DatasetError(f"Label column '{label_column}' not found. Columns: {list(df.columns)}")

    explicit_drop = [c.strip() for c in (drop_columns or []) if c.strip()]
    missing = [c for c in explicit_drop if c not in df.columns]
    if missing:
        raise DatasetError(f"Cannot drop {missing}: not in the file. Columns: {list(df.columns)}")
    if label_column and label_column in explicit_drop:
        raise DatasetError("The label column can't also be listed in drop_columns.")

    label_series = df[label_column] if label_column else None
    feature_df = df.drop(columns=[c for c in [label_column, *explicit_drop] if c])

    # Cleaning: numeric columns only (an Isolation Forest needs numeric
    # input), drop rows with any missing/infinite feature value.
    numeric_df = feature_df.select_dtypes(include=[np.number])
    non_numeric = set(feature_df.columns) - set(numeric_df.columns)
    dropped_columns = sorted(non_numeric | set(explicit_drop))
    numeric_df = numeric_df.dropna()
    if label_series is not None:
        label_series = label_series.loc[numeric_df.index]
        keep = label_series.notna()
        numeric_df, label_series = numeric_df[keep], label_series[keep]
        # a label column that had blanks is read as float (1.0, 0.0); put it
        # back to integers so "1" matches "1" rather than "1.0"
        if (
            pd.api.types.is_float_dtype(label_series)
            and len(label_series)
            and (label_series % 1 == 0).all()
        ):
            label_series = label_series.astype(int)

    if numeric_df.shape[1] == 0:
        raise DatasetError(
            "No numeric feature columns remain after cleaning. "
            f"Non-numeric columns dropped: {dropped_columns or feature_df.columns.tolist()}"
        )
    if len(numeric_df) == 0:
        raise DatasetError("No complete rows remain after dropping missing values.")

    processed = numeric_df.copy()
    if label_series is not None:
        processed[label_column] = label_series.values

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    processed_name = f"{Path(raw_filename).stem}.processed.csv"
    processed_path = PROCESSED_DIR / processed_name
    processed.to_csv(processed_path, index=False)

    label_distribution = None
    if label_series is not None:
        label_distribution = {str(k): int(v) for k, v in label_series.value_counts().items()}

    return {
        "processed_filename": processed_name,
        "num_records": len(numeric_df),
        "num_features": numeric_df.shape[1],
        "feature_names": numeric_df.columns.tolist(),
        "dropped_columns": dropped_columns,
        "rows_dropped": rows_read - len(numeric_df),
        "label_column": label_column,
        "label_distribution": label_distribution,
    }


def train_on_dataset(
    db: Session,
    processed_filename: str,
    label_column: str | None,
    attack_label_values: list[str] | None,
    contamination: float = 0.05,
    benign_label_values: list[str] | None = None,
) -> MLTrainingRun:
    processed_path = _resolve_inside(PROCESSED_DIR, processed_filename)
    if not processed_path.exists():
        raise DatasetError(f"No processed file named '{processed_filename}'. Preprocess it first.")

    df = pd.read_csv(processed_path)
    label_column = label_column.strip() if label_column else None
    if label_column and label_column not in df.columns:
        raise DatasetError(f"Label column '{label_column}' not in processed file.")

    y_true = None
    if label_column:
        y_true = attack_mask(df[label_column], attack_label_values, benign_label_values).astype(int).to_numpy()
        X = df.drop(columns=[label_column]).to_numpy(dtype=float)
        feature_names = df.drop(columns=[label_column]).columns.tolist()
    else:
        text_columns = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
        if text_columns:
            raise DatasetError(
                f"The processed file still has non-numeric column(s) {text_columns} — it was probably "
                "preprocessed with a label column. Pass label_column (and the attack/benign values), "
                "or preprocess the raw file again without a label column."
            )
        X = df.to_numpy(dtype=float)
        feature_names = df.columns.tolist()

    if len(df) < 5:
        raise DatasetError(f"Only {len(df)} row(s) after preprocessing; need at least 5 to train.")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(n_estimators=200, contamination=contamination, random_state=42)
    model.fit(X_scaled)
    predictions = model.predict(X_scaled)  # -1 = anomaly, 1 = normal
    y_pred = (predictions == -1).astype(int)
    anomalies_flagged = int(y_pred.sum())

    if y_true is not None:
        accuracy_status = "computed"
        evaluation: dict[str, Any] = {
            "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
            "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
            "true_positives": int(((y_pred == 1) & (y_true == 1)).sum()),
            "false_positives": int(((y_pred == 1) & (y_true == 0)).sum()),
            "true_negatives": int(((y_pred == 0) & (y_true == 0)).sum()),
            "false_negatives": int(((y_pred == 0) & (y_true == 1)).sum()),
            "note": "Computed against the dataset's own label column — a real, genuinely labeled evaluation.",
        }
        if attack_label_values:
            evaluation["attack_label_values"] = sorted(str(v) for v in attack_label_values)
        else:
            evaluation["benign_label_values"] = sorted(str(v) for v in (benign_label_values or []))
    else:
        accuracy_status = "not_applicable"
        evaluation = {
            "note": (
                "Unsupervised — no label column was given, so there is no ground truth to "
                "compare against. Accuracy/precision/recall are not computed."
            )
        }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    trained_at = datetime.now(timezone.utc)
    # Microsecond precision — see the matching comment in app/ml/train.py for why.
    model_version = f"dataset_isolation_forest_{trained_at.strftime('%Y%m%d_%H%M%S_%f')}"
    file_path = MODEL_DIR / f"{model_version}.joblib"
    joblib.dump({"model": model, "scaler": scaler, "features": feature_names}, file_path)

    run = MLTrainingRun(
        model_type="IsolationForest",
        model_version=model_version,
        training_dataset=processed_filename,
        num_samples=len(df),
        num_features=len(feature_names),
        feature_names=feature_names,
        contamination=contamination,
        accuracy_status=accuracy_status,
        evaluation=evaluation,
        anomalies_flagged=anomalies_flagged,
        file_path=str(file_path.relative_to(PROJECT_ROOT)),
        trained_at=trained_at,
        source="uploaded_dataset",
        dataset_filename=processed_filename,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
