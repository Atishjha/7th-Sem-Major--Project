export interface MLTrainingRun {
  id: number;
  model_type: string;
  model_version: string;
  training_dataset: string;
  num_samples: number;
  num_features: number;
  feature_names: string[];
  contamination: number;
  accuracy_status: string;
  evaluation: { note?: string };
  anomalies_flagged: number;
  trained_at: string;
}
export interface MLStatus {
  has_model: boolean;
  latest_run: MLTrainingRun | null;
}
export interface MLPrediction {
  id: number;
  source_ip: string;
  window_start: string;
  features: Record<string, number>;
  anomaly_score: number;
  is_anomalous: boolean;
}
