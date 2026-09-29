import { Fragment, useEffect, useMemo, useState } from "react";
import { Panel } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/SeverityBadge";
import { useEventStream } from "@/hooks/useEventStream";
import { getIncident, getIncidents } from "@/services/api";
import type { Incident, IncidentDetail } from "@/types/incident";

const SEVERITIES = ["low", "medium", "high", "critical"];

function mergeIncidents(base: Incident[], incoming: Incident[]): Incident[] {
  const byId = new Map(base.map((i) => [i.incident_id, i]));
  for (const inc of incoming) byId.set(inc.incident_id, inc);
  return [...byId.values()].sort((a, b) => b.last_seen.localeCompare(a.last_seen));
}

const ENTITY_LABELS: Record<string, string> = {
  usernames: "Users",
  source_ips: "Source IPs",
  hostnames: "Hosts",
  destination_ips: "Destinations",
};

export default function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<IncidentDetail | null>(null);
  const { connected, liveIncidents } = useEventStream();

  useEffect(() => {
    getIncidents({ limit: 100 })
      .then(setIncidents)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (liveIncidents.length === 0) return;
    setIncidents((prev) => mergeIncidents(prev, liveIncidents));
  }, [liveIncidents]);

  // keep the open detail panel current while alerts keep joining the incident
  useEffect(() => {
    if (!expandedId) return;
    getIncident(expandedId).then(setDetail);
  }, [expandedId, liveIncidents]);

  const filtered = useMemo(
    () => incidents.filter((i) => !severityFilter || i.severity === severityFilter),
    [incidents, severityFilter]
  );

  function toggle(id: string) {
    if (expandedId === id) {
      setExpandedId(null);
      setDetail(null);
    } else {
      setDetail(null);
      setExpandedId(id);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Incidents</h1>
          <p className="text-sm text-muted mt-1">
            Alerts that share a user, IP, host, or destination within 15 minutes
            are grouped into one incident. Open a row to see why.
          </p>
        </div>
        <span className="flex items-center gap-1.5 text-xs text-muted font-mono">
          <span
            className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-signal" : "bg-severity-medium"}`}
          />
          {connected ? "live" : "reconnecting…"}
        </span>
      </div>

      <select
        value={severityFilter}
        onChange={(e) => setSeverityFilter(e.target.value)}
        className="rounded-sm border border-line bg-ink-800 px-2 py-1.5 text-sm text-slate-200"
      >
        <option value="">All severities</option>
        {SEVERITIES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <Panel title={`Incidents (${filtered.length})`}>
        {loading ? (
          <p className="text-sm text-muted font-mono">Loading…</p>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-muted font-mono">
            No incidents yet. Run a scenario from Demo Mode; the multi-stage
            scenario groups four alerts into one.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-left text-muted border-b border-line">
                  <th className="py-1.5 pr-4">Last seen</th>
                  <th className="py-1.5 pr-4">ID</th>
                  <th className="py-1.5 pr-4">Severity</th>
                  <th className="py-1.5 pr-4">Incident</th>
                  <th className="py-1.5 pr-4">Alerts</th>
                  <th className="py-1.5 pr-4">Risk</th>
                  <th className="py-1.5 pr-4">Host / IP</th>
                  <th className="py-1.5">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((inc) => {
                  const open = expandedId === inc.incident_id;
                  return (
                    <Fragment key={inc.incident_id}>
                      <tr
                        onClick={() => toggle(inc.incident_id)}
                        className={`border-b border-line/50 cursor-pointer hover:bg-ink-800/40 ${
                          open ? "bg-ink-800/40" : ""
                        }`}
                      >
                        <td className="py-1.5 pr-4 text-muted whitespace-nowrap">
                          {new Date(inc.last_seen).toLocaleTimeString()}
                        </td>
                        <td className="py-1.5 pr-4 text-slate-400">{inc.incident_id}</td>
                        <td className="py-1.5 pr-4">
                          <SeverityBadge severity={inc.severity} />
                        </td>
                        <td className="py-1.5 pr-4 text-slate-200">{inc.title}</td>
                        <td className="py-1.5 pr-4 text-signal">{inc.alert_count}</td>
                        <td className="py-1.5 pr-4">
                          {inc.risk_score !== null ? (
                            <span
                              className={
                                inc.risk_score >= 75
                                  ? "text-severity-critical"
                                  : inc.risk_score >= 50
                                    ? "text-severity-high"
                                    : "text-severity-medium"
                              }
                            >
                              {Math.round(inc.risk_score)}/100
                            </span>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                        <td className="py-1.5 pr-4 text-slate-400">
                          {inc.primary_hostname ?? "—"} / {inc.primary_source_ip ?? "—"}
                        </td>
                        <td className="py-1.5">
                          <Badge tone="neutral">{inc.status}</Badge>
                        </td>
                      </tr>

                      {open && (
                        <tr className="border-b border-line/50">
                          <td colSpan={8} className="bg-ink-950/60 px-4 py-4">
                            {!detail || detail.incident_id !== inc.incident_id ? (
                              <p className="text-muted">Loading correlation trail…</p>
                            ) : (
                              <div className="space-y-4">
                                <div className="flex flex-wrap gap-x-8 gap-y-2">
                                  {Object.entries(detail.incident_metadata.entities ?? {}).map(
                                    ([key, values]) =>
                                      values && values.length > 0 ? (
                                        <div key={key}>
                                          <div className="text-muted mb-1">
                                            {ENTITY_LABELS[key] ?? key}
                                          </div>
                                          <div className="flex flex-wrap gap-1.5">
                                            {values.map((v) => (
                                              <Badge key={v} tone="neutral">
                                                {v}
                                              </Badge>
                                            ))}
                                          </div>
                                        </div>
                                      ) : null
                                  )}
                                  <div>
                                    <div className="text-muted mb-1">Evidence</div>
                                    <span className="text-slate-200">
                                      {detail.event_ids.length} linked events
                                    </span>
                                  </div>
                                </div>

                                {detail.incident_metadata.risk_breakdown && (
                                  <div>
                                    <div className="flex items-baseline gap-2 mb-2">
                                      <span className="text-muted">Risk score</span>
                                      <span className="text-slate-100 text-base">
                                        {Math.round(detail.risk_score ?? 0)}/100
                                      </span>
                                    </div>
                                    <div className="space-y-1.5">
                                      {detail.incident_metadata.risk_breakdown.map((f) => (
                                        <div key={f.factor} className="flex items-center gap-3">
                                          <span className="w-40 shrink-0 text-slate-300">{f.label}</span>
                                          <div className="flex-1 h-2 bg-ink-950 rounded-full overflow-hidden">
                                            <div
                                              className="h-full bg-signal"
                                              style={{ width: `${(f.points / f.max_points) * 100}%` }}
                                            />
                                          </div>
                                          <span className="w-16 text-right text-slate-200">
                                            +{f.points}/{f.max_points}
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                <div>
                                  <div className="text-muted mb-2">
                                    Why these alerts are one incident
                                  </div>
                                  <div className="space-y-2.5">
                                    {detail.alerts.map((a) => {
                                      const trail = detail.incident_metadata.correlation?.find(
                                        (c) => c.alert_id === a.alert_id
                                      );
                                      return (
                                        <div key={a.alert_id} className="flex gap-3">
                                          <span className="text-muted whitespace-nowrap pt-0.5">
                                            {new Date(a.detected_at).toLocaleTimeString()}
                                          </span>
                                          <div className="min-w-0">
                                            <div className="flex items-center gap-2">
                                              <span className="text-slate-400">{a.alert_id}</span>
                                              <SeverityBadge severity={a.severity} />
                                              <span className="text-signal">{a.rule_name}</span>
                                            </div>
                                            <div className="text-slate-400 mt-0.5">
                                              {trail && trail.score > 0
                                                ? `score ${trail.score}: ${trail.reasons.join("; ")}`
                                                : "first alert, opened this incident"}
                                            </div>
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
