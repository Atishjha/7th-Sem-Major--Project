import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Panel } from "@/components/ui/panel";
import { SeverityBadge } from "@/components/SeverityBadge";
import { getAiStatus, getIncidents } from "@/services/api";
import type { AiStatus } from "@/services/api";
import { Badge } from "@/components/ui/badge";
import type { Incident } from "@/types/incident";

export default function AiAnalyst() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [ai, setAi] = useState<AiStatus | null>(null);

  useEffect(() => {
    getAiStatus().then(setAi).catch(() => setAi(null));
    getIncidents({ limit: 100 })
      .then(setIncidents)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">AI SOC Analyst</h1>
        <p className="text-sm text-muted mt-1">
          Pick an incident and ask the analyst to investigate it. The report is generated from the
          incident&apos;s real alerts, events, risk breakdown and MITRE mapping.
        </p>
      </div>

      {ai && (
        <Panel title="Who answers right now">
          <div className="px-4 py-3 flex flex-wrap items-center gap-3 text-xs font-mono">
            <Badge tone={ai.mode === "live" ? "signal" : "neutral"}>{ai.mode === "live" ? "live model" : "offline mock"}</Badge>
            <span className="text-slate-200">{ai.label}</span>
            {ai.note && <span className="text-muted">{ai.note}</span>}
          </div>
        </Panel>
      )}

      <Panel title="How it works">
        <ul className="space-y-1.5 text-xs text-muted list-disc pl-4">
          <li>
            <span className="text-slate-200">Facts and interpretation are kept apart:</span> every report
            separates <em>observed evidence</em> from <em>inference</em>, and lists what is still unknown.
          </li>
          <li>
            <span className="text-slate-200">Works offline by default.</span> The built-in mock analyst
            needs no API key. A real LLM can be enabled in the server configuration.
          </li>
          <li>
            <span className="text-slate-200">Never leaves you without a report:</span> if the configured LLM
            is unreachable or returns something unusable, the mock analyst answers instead, and the
            report says so.
          </li>
          <li>
            <span className="text-slate-200">Advisory only.</span> Recommended containment goes to the
            Response Center, where an analyst approves or rejects it; approvals are simulated.
          </li>
        </ul>
      </Panel>

      <Panel title={`Investigate an incident (${incidents.length})`}>
        {loading ? (
          <p className="text-sm text-muted font-mono">Loading…</p>
        ) : incidents.length === 0 ? (
          <p className="text-sm text-muted font-mono">
            No incidents yet. Run a scenario from Demo Mode, then come back.
          </p>
        ) : (
          <ul className="divide-y divide-line/50">
            {incidents.map((inc) => (
              <li key={inc.incident_id} className="flex items-center gap-3 py-2 text-xs font-mono">
                <span className="w-24 text-slate-400">{inc.incident_id}</span>
                <SeverityBadge severity={inc.severity} />
                <span className="flex-1 truncate text-slate-200">{inc.title}</span>
                <Link
                  to={`/incidents/${inc.incident_id}`}
                  className="text-signal hover:underline whitespace-nowrap"
                >
                  Open investigation →
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
