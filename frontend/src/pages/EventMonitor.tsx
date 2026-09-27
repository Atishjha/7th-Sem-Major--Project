import { useEffect, useMemo, useState } from "react";
import { Panel } from "@/components/ui/panel";
import { SeverityBadge } from "@/components/SeverityBadge";
import { useEventStream } from "@/hooks/useEventStream";
import { getEvents } from "@/services/api";
import type { SocEvent } from "@/types/event";

const SOURCES = ["authentication", "endpoint", "network", "dns"];
const SEVERITIES = ["low", "medium", "high", "critical"];

function mergeEvents(base: SocEvent[], incoming: SocEvent[]): SocEvent[] {
  const seen = new Set(base.map((e) => e.event_id));
  const fresh = incoming.filter((e) => !seen.has(e.event_id));
  return [...fresh, ...base].slice(0, 300);
}

export default function EventMonitor() {
  const [events, setEvents] = useState<SocEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [sourceFilter, setSourceFilter] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const { connected, liveEvents } = useEventStream();

  useEffect(() => {
    getEvents({ limit: 100 })
      .then(setEvents)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (liveEvents.length === 0) return;
    setEvents((prev) => mergeEvents(prev, liveEvents));
  }, [liveEvents]);

  const filtered = useMemo(
    () =>
      events.filter(
        (e) =>
          (!sourceFilter || e.source === sourceFilter) &&
          (!severityFilter || e.severity === severityFilter)
      ),
    [events, sourceFilter, severityFilter]
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">Event Monitor</h1>
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
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="rounded-sm border border-line bg-ink-800 px-2 py-1.5 text-sm text-slate-200"
        >
          <option value="">All sources</option>
          {SOURCES.map((s) => (
            <option key={s} value={s}>
              {s}
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

      <Panel title={`Events (${filtered.length})`}>
        {loading ? (
          <p className="text-sm text-muted font-mono">Loading…</p>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-muted font-mono">No events match this filter.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-left text-muted border-b border-line">
                  <th className="py-1.5 pr-4">Time</th>
                  <th className="py-1.5 pr-4">ID</th>
                  <th className="py-1.5 pr-4">Source</th>
                  <th className="py-1.5 pr-4">Severity</th>
                  <th className="py-1.5 pr-4">User / Host</th>
                  <th className="py-1.5 pr-4">Source IP</th>
                  <th className="py-1.5">Message</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => (
                  <tr key={e.event_id} className="border-b border-line/50">
                    <td className="py-1.5 pr-4 text-muted whitespace-nowrap">
                      {new Date(e.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="py-1.5 pr-4 text-muted">{e.event_id}</td>
                    <td className="py-1.5 pr-4 text-signal">{e.source}</td>
                    <td className="py-1.5 pr-4">
                      <SeverityBadge severity={e.severity} />
                    </td>
                    <td className="py-1.5 pr-4 text-slate-300">
                      {e.username ?? "—"} {e.hostname ? `@ ${e.hostname}` : ""}
                    </td>
                    <td className="py-1.5 pr-4 text-slate-400">{e.source_ip ?? "—"}</td>
                    <td className="py-1.5 text-slate-200">{e.message}</td>
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
