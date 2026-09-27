export type Severity = "low" | "medium" | "high" | "critical";

export interface SocEvent {
  id: number;
  event_id: string;
  timestamp: string;
  source: string;
  source_ip: string | null;
  destination_ip: string | null;
  username: string | null;
  hostname: string | null;
  event_type: string;
  action: string;
  status: string;
  severity: Severity;
  message: string;
  event_metadata: Record<string, unknown>;
}

export type ScenarioName =
  | "brute_force"
  | "powershell"
  | "dns_anomaly"
  | "network_anomaly"
  | "multi_stage";

export interface SimulatorStatus {
  running: boolean;
  scenario: ScenarioName | null;
  events_emitted: number;
  total_events: number | null;
  started_at: string | null;
}

export type WsMessage =
  | { type: "event"; data: SocEvent }
  | { type: "status"; data: SimulatorStatus };
