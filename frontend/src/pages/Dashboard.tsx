import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Panel } from "@/components/ui/panel";
import { SeverityBadge } from "@/components/SeverityBadge";
import { useEventStream } from "@/hooks/useEventStream";
import { getDashboard } from "@/services/api";
import type { DashboardResponse } from "@/types/dashboard";

const SEVERITY_COLORS: Record<string, string> = {
  low: "#3B82F6",
  medium: "#D9A441",
  high: "#E8743B",
  critical: "#E14F4F",
};

const STAT_STRIP: Array<{
  key: keyof DashboardResponse["kpis"];
  label: string;
  format?: (v: number | null) => string;
}> = [
  { key: "critical_alerts", label: "Critical alerts" },
  { key: "events_processed", label: "Events processed" },
  { key: "anomalies_detected", label: "Anomalies detected" },
  {
    key: "detection_rate_pct",
    label: "Detection rate",
    format: (v) => (v === null ? "—" : `${v}%`),
  },
  {
    key: "avg_response_time_seconds",
    label: "Avg response time",
    format: (v) => (v === null ? "—" : `${v}s`),
  },
  { key: "systems_at_risk", label: "Systems at risk" },
];

function EmptyChart({ note }: { note: string }) {
  return (
    <div className="h-48 flex items-center justify-center text-xs text-muted font-mono text-center px-6">
      {note}
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { connected, liveEvents, status } = useEventStream();

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((e) => setError(e.message ?? "Failed to load dashboard"));
  }, []);

  if (error) {
    return (
      <Panel title="Dashboard">
        <p className="text-sm text-severity-critical">{error}</p>
      </Panel>
    );
  }

  if (!data) {
    return (
      <div className="text-sm text-muted font-mono">Loading telemetry…</div>
    );
  }

  const { kpis, charts, live_events, message } = data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">Dashboard</h1>
        <p className="text-sm text-muted mt-1">{message}</p>
      </div>

      {/* KPI hero + stat strip */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <Panel className="lg:col-span-1">
          <div className="text-xs text-muted mb-1">Active incidents</div>
          <div className="text-4xl font-semibold font-mono text-slate-100">
            {kpis.active_incidents}
          </div>
        </Panel>

        <Panel className="lg:col-span-3">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 divide-x divide-line">
            {STAT_STRIP.map(({ key, label, format }) => {
              const raw = kpis[key];
              return (
                <div key={key} className="px-4 first:pl-0">
                  <div className="text-xs text-muted mb-1">{label}</div>
                  <div className="text-xl font-mono text-slate-100">
                    {format ? format(raw as number | null) : raw}
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      </div>

      {/* Row 2: events over time + severity distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="Events over time">
          {charts.events_over_time.length === 0 ? (
            <EmptyChart note="No events yet — run a scenario from Demo Mode or seed baseline data." />
          ) : (
            <ResponsiveContainer width="100%" height={192}>
              <AreaChart data={charts.events_over_time}>
                <CartesianGrid stroke="#1E2A42" strokeDasharray="3 3" />
                <XAxis dataKey="label" stroke="#7E8CA6" fontSize={11} />
                <YAxis stroke="#7E8CA6" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: "#121B2E",
                    border: "1px solid #1E2A42",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#33C3A6"
                  fill="#33C3A6"
                  fillOpacity={0.15}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel title="Severity distribution">
          {charts.severity_distribution.length === 0 ? (
            <EmptyChart note="No alerts yet — populated once the Detection Engine (Phase 5) is live." />
          ) : (
            <ResponsiveContainer width="100%" height={192}>
              <PieChart>
                <Pie
                  data={charts.severity_distribution}
                  dataKey="count"
                  nameKey="category"
                  innerRadius={50}
                  outerRadius={80}
                >
                  {charts.severity_distribution.map((entry) => (
                    <Cell
                      key={entry.category}
                      fill={SEVERITY_COLORS[entry.category] ?? "#7E8CA6"}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "#121B2E",
                    border: "1px solid #1E2A42",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      {/* Row 3: detection type + attack category */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="Detection type">
          {charts.detection_type_distribution.length === 0 ? (
            <EmptyChart note="No detections yet — the Rule/ML Detection Engine arrives in Phase 5–6." />
          ) : (
            <ResponsiveContainer width="100%" height={192}>
              <BarChart data={charts.detection_type_distribution}>
                <CartesianGrid stroke="#1E2A42" strokeDasharray="3 3" />
                <XAxis dataKey="category" stroke="#7E8CA6" fontSize={11} />
                <YAxis stroke="#7E8CA6" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: "#121B2E",
                    border: "1px solid #1E2A42",
                  }}
                />
                <Bar dataKey="count" fill="#33C3A6" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel title="Attack category">
          {charts.attack_category_distribution.length === 0 ? (
            <EmptyChart note="No mapped attacks yet — arrives with MITRE ATT&CK mapping in Phase 11." />
          ) : (
            <ResponsiveContainer width="100%" height={192}>
              <BarChart data={charts.attack_category_distribution}>
                <CartesianGrid stroke="#1E2A42" strokeDasharray="3 3" />
                <XAxis dataKey="category" stroke="#7E8CA6" fontSize={11} />
                <YAxis stroke="#7E8CA6" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: "#121B2E",
                    border: "1px solid #1E2A42",
                  }}
                />
                <Bar dataKey="count" fill="#E8743B" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      {/* Row 4: ML anomalies + incident timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="ML anomalies over time">
          {charts.ml_anomalies_over_time.length === 0 ? (
            <EmptyChart note="No anomaly scores yet — the Isolation Forest model arrives in Phase 6." />
          ) : (
            <ResponsiveContainer width="100%" height={192}>
              <LineChart data={charts.ml_anomalies_over_time}>
                <CartesianGrid stroke="#1E2A42" strokeDasharray="3 3" />
                <XAxis dataKey="label" stroke="#7E8CA6" fontSize={11} />
                <YAxis stroke="#7E8CA6" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: "#121B2E",
                    border: "1px solid #1E2A42",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#D9A441"
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel title="Incident timeline">
          <EmptyChart note="No incidents yet — Alert Correlation and Incident Management arrive in Phase 7–9." />
        </Panel>
      </div>

      {/* Live event stream */}
      <Panel
        title="Live event stream"
        aside={
          <span className="flex items-center gap-1.5 text-xs text-muted font-mono">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                status?.running ? "bg-signal" : connected ? "bg-severity-medium" : "bg-severity-critical"
              }`}
            />
            {status?.running
              ? `running: ${status.scenario}`
              : connected
                ? "listening — simulator idle"
                : "disconnected"}
          </span>
        }
      >
        {liveEvents.length === 0 && live_events.length === 0 ? (
          <p className="text-xs text-muted font-mono">
            No live telemetry yet. Start a scenario from Demo Mode to see
            events stream in here over WebSockets.
          </p>
        ) : (
          <div className="space-y-1 font-mono text-xs max-h-48 overflow-y-auto">
            {liveEvents.length > 0
              ? liveEvents.map((ev) => (
                  <div key={ev.event_id} className="flex items-center gap-2 text-slate-300">
                    <span className="text-muted whitespace-nowrap">
                      {new Date(ev.timestamp).toLocaleTimeString()}
                    </span>
                    <SeverityBadge severity={ev.severity} />
                    <span className="text-signal">{ev.source}</span>
                    <span>{ev.message}</span>
                  </div>
                ))
              : live_events.map((ev, i) => (
                  <div key={i} className="text-slate-300">
                    <span className="text-muted">{ev.timestamp}</span>{" "}
                    <span className="text-signal">{ev.source}</span> {ev.message}
                  </div>
                ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
