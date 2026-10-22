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
  evaluation: {
    note?: string;
    accuracy?: number;
    precision?: number;
    recall?: number;
    f1?: number;
    true_positives?: number;
    false_positives?: number;
    true_negatives?: number;
    false_negatives?: number;
    attack_label_values?: string[];
  };
  anomalies_flagged: number;
  trained_at: string;
  source: string;
  dataset_filename: string | null;
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
