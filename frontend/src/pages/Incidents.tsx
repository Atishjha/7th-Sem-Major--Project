import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Panel } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/SeverityBadge";
import { useEventStream } from "@/hooks/useEventStream";
import { getIncidents } from "@/services/api";
import type { Incident } from "@/types/incident";

const SEVERITIES = ["low", "medium", "high", "critical"];

function mergeIncidents(base: Incident[], incoming: Incident[]): Incident[] {
  const byId = new Map(base.map((i) => [i.incident_id, i]));
  for (const inc of incoming) byId.set(inc.incident_id, inc);
  return [...byId.values()].sort((a, b) => b.last_seen.localeCompare(a.last_seen));
}

export default function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState("");
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

  const filtered = useMemo(
    () => incidents.filter((i) => !severityFilter || i.severity === severityFilter),
    [incidents, severityFilter]
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Incidents</h1>
          <p className="text-sm text-muted mt-1">
            Alerts that share a user, IP, host, or destination within 15 minutes
            are grouped into one incident. Open one for the full investigation view.
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
                {filtered.map((inc) => (
                  <tr
                    key={inc.incident_id}
                    className="border-b border-line/50 hover:bg-ink-800/40"
                  >
                    <td className="py-1.5 pr-4">
                      <Link to={`/incidents/${inc.incident_id}`} className="contents">
                        <span className="text-muted whitespace-nowrap">
                          {new Date(inc.last_seen).toLocaleTimeString()}
                        </span>
                      </Link>
                    </td>
                    <td className="py-1.5 pr-4">
                      <Link
                        to={`/incidents/${inc.incident_id}`}
                        className="text-slate-400 hover:text-signal hover:underline"
                      >
                        {inc.incident_id}
                      </Link>
                    </td>
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
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
