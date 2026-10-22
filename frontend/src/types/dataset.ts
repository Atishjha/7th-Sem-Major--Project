import type { MLTrainingRun } from "@/types/ml";

export interface DatasetFile {
  filename: string;
  size_bytes: number;
  modified_at: string;
}

export interface DatasetFiles {
  raw: DatasetFile[];
  processed: DatasetFile[];
}

export interface PreprocessResult {
  processed_filename: string;
  num_records: number;
  num_features: number;
  feature_names: string[];
  dropped_columns: string[];
  label_column: string | null;
  label_distribution: Record<string, number> | null;
}

export type DatasetTrainingRun = MLTrainingRun;
