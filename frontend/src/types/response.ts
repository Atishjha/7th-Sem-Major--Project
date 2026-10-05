export type ActionType =
  | "disable_account"
  | "revoke_session"
  | "isolate_endpoint"
  | "block_indicator"
  | "reset_credentials"
  | "create_firewall_rule";

export type ActionStatus = "recommended" | "rejected" | "simulated_success";

export interface ResponseAction {
  id: number;
  response_id: string;
  incident_id: number;
  action_type: ActionType;
  action_label: string;
  target: string;
  recommended_reason: string;
  status: ActionStatus;
  result_message: string | null;
  decided_by_username: string | null;
  decided_at: string | null;
  created_at: string;
}
