import type { Alert, Severity, SocEvent } from "@/types/event";

export interface CorrelationEntry {
  alert_id: string;
  rule_key: string;
  score: number;
  reasons: string[];
}

export interface RiskFactor {
  factor: string;
  label: string;
  points: number;
  max_points: number;
  detail: string | Record<string, unknown>;
}

export interface IncidentMetadata {
  risk_breakdown?: RiskFactor[];
  entities?: Partial<
    Record<"usernames" | "source_ips" | "hostnames" | "destination_ips", string[]>
  >;
  rule_keys?: string[];
  correlation?: CorrelationEntry[];
}

export interface Incident {
  id: number;
  incident_id: string;
  title: string;
  incident_type: string;
  severity: Severity;
  status: string;
  primary_username: string | null;
  primary_source_ip: string | null;
  primary_hostname: string | null;
  first_seen: string;
  last_seen: string;
  alert_count: number;
  risk_score: number | null;
  incident_metadata: IncidentMetadata;
  created_at: string;
}

export interface IncidentDetail extends Incident {
  alerts: Alert[];
  events: SocEvent[];
}
