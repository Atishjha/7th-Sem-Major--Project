import type { LoginResponse, User } from "@/types/auth";
import type { DashboardResponse } from "@/types/dashboard";
import type { SocEvent, SimulatorStatus, ScenarioName } from "@/types/event";

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
