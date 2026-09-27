import { useEffect, useMemo, useState } from "react";
import { Panel } from "@/components/ui/panel";
import { SeverityBadge } from "@/components/SeverityBadge";
import { useEventStream } from "@/hooks/useEventStream";
import { getAlerts } from "@/services/api";
import type { Alert } from "@/types/event";
const SEVERITIES = ["low", "medium", "high", "critical"];
function mergeAlerts(base: Alert[], incoming: Alert[]): Alert[] {
  const seen = new Set(base.map((a) => a.alert_id));
  const fresh = incoming.filter((a) => !seen.has(a.alert_id));
  return [...fresh, ...base].slice(0, 300);
}
export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [ruleFilter, setRuleFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const { connected, liveAlerts } = useEventStream();

  useEffect(() => {
    getAlerts({ limit: 100 })
      .then(setAlerts)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (liveAlerts.length === 0) return;
    setAlerts((prev) => mergeAlerts(prev, liveAlerts));
  }, [liveAlerts]);

  const ruleOptions = useMemo(
    () => Array.from(new Set(alerts.map((a) => a.rule_key))).sort(),
    [alerts]
  );

  const filtered = useMemo(
    () =>
      alerts.filter(
        (a) =>
          (!ruleFilter || a.rule_key === ruleFilter) &&
          (!severityFilter || a.severity === severityFilter)
      ),
    [alerts, ruleFilter, severityFilter]
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">Alerts</h1>
        <span className="flex items-center gap-1.5 text-xs text-muted font-mono">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              connected ? "bg-signal" : "bg-severity-medium"
            }`}
          />
          {connected ? "live" : "reconnecting…"}
        </span>
      </div>

      <div className="flex gap-3">
        <select
          value={ruleFilter}
          onChange={(e) => setRuleFilter(e.target.value)}
          className="rounded-sm border border-line bg-ink-800 px-2 py-1.5 text-sm text-slate-200"
        >
          <option value="">All rules</option>
          {ruleOptions.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>

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
      </div>

      <Panel title={`Alerts (${filtered.length})`}>
        {loading ? (
          <p className="text-sm text-muted font-mono">Loading…</p>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-muted font-mono">
            No alerts yet — run a scenario from Demo Mode to trigger the
            detection rules.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-left text-muted border-b border-line">
                  <th className="py-1.5 pr-4">Time</th>
                  <th className="py-1.5 pr-4">ID</th>
                  <th className="py-1.5 pr-4">Rule</th>
                  <th className="py-1.5 pr-4">Severity</th>
                  <th className="py-1.5 pr-4">User / Host</th>
                  <th className="py-1.5 pr-4">Source IP</th>
                  <th className="py-1.5">Title</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => (
                  <tr key={a.alert_id} className="border-b border-line/50">
                    <td className="py-1.5 pr-4 text-muted whitespace-nowrap">
                      {new Date(a.detected_at).toLocaleTimeString()}
                    </td>
                    <td className="py-1.5 pr-4 text-muted">{a.alert_id}</td>
                    <td className="py-1.5 pr-4 text-signal">{a.rule_name}</td>
                    <td className="py-1.5 pr-4">
                      <SeverityBadge severity={a.severity} />
                    </td>
                    <td className="py-1.5 pr-4 text-slate-300">
                      {a.username ?? "—"} {a.hostname ? `@ ${a.hostname}` : ""}
                    </td>
                    <td className="py-1.5 pr-4 text-slate-400">{a.source_ip ?? "—"}</td>
                    <td className="py-1.5 text-slate-200">{a.title}</td>
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
