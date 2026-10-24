from typing import Any

from pydantic import BaseModel, Field


class DatasetFileOut(BaseModel):
    filename: str
    size_bytes: int
    modified_at: str


class DatasetFilesOut(BaseModel):
    raw: list[DatasetFileOut]
    processed: list[DatasetFileOut]


class PreprocessRequest(BaseModel):
    raw_filename: str
    label_column: str | None = None


class PreprocessResultOut(BaseModel):
    processed_filename: str
    num_records: int
    num_features: int
    feature_names: list[str]
    dropped_columns: list[str]
    rows_dropped: int = 0
    label_column: str | None
    label_distribution: dict[str, int] | None


class TrainDatasetRequest(BaseModel):
    processed_filename: str
    label_column: str | None = None
    attack_label_values: list[str] | None = None
    contamination: float = Field(0.05, gt=0, le=0.5)
