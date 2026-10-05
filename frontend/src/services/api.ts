import type { LoginResponse, User } from "@/types/auth";
import type { DashboardResponse } from "@/types/dashboard";
import type { SocEvent, SimulatorStatus, ScenarioName, Alert, DetectionRule } from "@/types/event";
import type { MLStatus, MLPrediction, MLTrainingRun } from "@/types/ml";
import type { Incident, IncidentDetail } from "@/types/incident";
import type { Investigation } from "@/types/ai";
import type { TechniqueObservation } from "@/types/mitre";
import type { MitreTechnique } from "@/types/ai";
import type { ResponseAction } from "@/types/response";
import type { AuditLogEntry } from "@/types/audit";

const API_BASE = "/api";
const TOKEN_KEY = "soc_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers ?? {}),
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    if (res.status === 401) clearToken();
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  time: string;
}

export const getHealth = () => request<HealthResponse>("/health");

export const login = (username: string, password: string) =>
  request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

export const getMe = () => request<User>("/auth/me");

export const getDashboard = () => request<DashboardResponse>("/dashboard");

export const getEvents = (params: { limit?: number; source?: string; severity?: string } = {}) => {
  const qs = new URLSearchParams();
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.source) qs.set("source", params.source);
  if (params.severity) qs.set("severity", params.severity);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<SocEvent[]>(`/events${suffix}`);
};

export const getSimulatorStatus = () => request<SimulatorStatus>("/simulator/status");

export const startSimulator = (scenario: ScenarioName) =>
  request<SimulatorStatus>("/simulator/start", {
    method: "POST",
    body: JSON.stringify({ scenario }),
  });

export const stopSimulator = () =>
  request<SimulatorStatus>("/simulator/stop", { method: "POST" });

export const getAlerts = (params: { limit?: number; rule_key?: string; severity?: string } = {}) => {
  const qs = new URLSearchParams();
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.rule_key) qs.set("rule_key", params.rule_key);
  if (params.severity) qs.set("severity", params.severity);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<Alert[]>(`/alerts${suffix}`);
};

export const getRules = () => request<DetectionRule[]>("/rules");

export const updateRule = (
  rule_key: string,
  updates: { enabled?: boolean; config?: Record<string, number | string> }
) =>
  request<DetectionRule>("/rules", {
    method: "POST",
    body: JSON.stringify({ rule_key, ...updates }),
  });

export const getMlStatus = () => request<MLStatus>("/ml/status");

export const trainMlModel = (contamination = 0.05, window_minutes = 5) =>
  request<MLTrainingRun>("/ml/train", {
    method: "POST",
    body: JSON.stringify({ contamination, window_minutes }),
  });

export const getMlPredictions = (params: { limit?: number; anomalous_only?: boolean } = {}) => {
  const qs = new URLSearchParams();
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.anomalous_only) qs.set("anomalous_only", "true");
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<MLPrediction[]>(`/ml/predictions${suffix}`);
};

export const getIncidents = (params: { limit?: number; status?: string; severity?: string } = {}) => {
  const qs = new URLSearchParams();
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.status) qs.set("status", params.status);
  if (params.severity) qs.set("severity", params.severity);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<Incident[]>(`/incidents${suffix}`);
};

export const getIncident = (incidentId: string) =>
  request<IncidentDetail>(`/incidents/${incidentId}`);

export const investigateIncident = (incidentId: string) =>
  request<Investigation>(`/incidents/${incidentId}/investigate`, { method: "POST" });

export const getInvestigation = (incidentId: string) =>
  request<Investigation | null>(`/incidents/${incidentId}/investigation`);

export const getMitreTechniques = () => request<TechniqueObservation[]>("/mitre/techniques");

export const getIncidentMitre = (incidentId: string) =>
  request<MitreTechnique[]>(`/incidents/${incidentId}/mitre`);

export const getIncidentResponseActions = (incidentId: string) =>
  request<ResponseAction[]>(`/incidents/${incidentId}/response`);

export const getAllResponseActions = (statusFilter?: string) => {
  const suffix = statusFilter ? `?status_filter=${statusFilter}` : "";
  return request<ResponseAction[]>(`/response${suffix}`);
};

export const approveResponseAction = (responseId: string) =>
  request<ResponseAction>(`/response/${responseId}/approve`, { method: "POST" });

export const rejectResponseAction = (responseId: string) =>
  request<ResponseAction>(`/response/${responseId}/reject`, { method: "POST" });

export const getAuditLogs = (
  params: { limit?: number; resource_type?: string; resource_id?: string; username?: string } = {}
) => {
  const qs = new URLSearchParams();
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.resource_type) qs.set("resource_type", params.resource_type);
  if (params.resource_id) qs.set("resource_id", params.resource_id);
  if (params.username) qs.set("username", params.username);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<AuditLogEntry[]>(`/audit${suffix}`);
};
