export interface DashboardKpis {
  active_incidents: number;
  critical_alerts: number;
  events_processed: number;
  anomalies_detected: number;
  detection_rate_pct: number | null;
  avg_response_time_seconds: number | null;
  systems_at_risk: number;
}

export interface TimeSeriesPoint {
  label: string;
  value: number;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface DashboardCharts {
  events_over_time: TimeSeriesPoint[];
  severity_distribution: CategoryCount[];
  detection_type_distribution: CategoryCount[];
  attack_category_distribution: CategoryCount[];
  ml_anomalies_over_time: TimeSeriesPoint[];
}

export interface LiveEvent {
  timestamp: string;
  source: string;
  message: string;
}

export interface DashboardResponse {
  kpis: DashboardKpis;
  charts: DashboardCharts;
  live_events: LiveEvent[];
  data_status: "no_data" | "live";
  message: string;
}
