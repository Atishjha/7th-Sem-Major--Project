import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Panel } from "@/components/ui/panel";
import { SeverityBadge } from "@/components/SeverityBadge";
import { getIncidents } from "@/services/api";
import type { Incident } from "@/types/incident";

// Mirrors backend/app/services/risk_engine.py (maxima sum to 100).
const FACTORS = [
  { name: "Severity", max: 30, what: "The incident's worst alert severity." },
  { name: "Asset criticality", max: 20, what: "How important the affected host is (registered assets; unknown hosts get a medium default)." },
  { name: "Detection confidence", max: 15, what: "The configured confidence of the rule(s) that fired; the highest wins." },
  { name: "Correlated alerts", max: 20, what: "4 points per alert grouped into the incident, capped at 20." },
  { name: "ML anomaly", max: 15, what: "The anomaly score of the incident's source IP from the latest trained model; 0 if none." },
];

function riskColor(score: number) {
  return score >= 75 ? "bg-severity-critical" : score >= 50 ? "bg-severity-high" : "bg-severity-medium";
}

export default function RiskEngine() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getIncidents({ limit: 100 })
      .then(setIncidents)
      .finally(() => setLoading(false));
  }, []);

  const ranked = useMemo(
    () => [...incidents].sort((a, b) => (b.risk_score ?? -1) - (a.risk_score ?? -1)),
    [incidents]
  );

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">Risk Engine</h1>
        <p className="text-sm text-muted mt-1">
          Every incident gets a 0–100 score built from five real, inspectable factors. Nothing is
          hidden: open an incident to see the points each factor contributed.
        </p>
      </div>

      <Panel title="How the score is built">
        <table className="w-full text-xs font-mono">
          <tbody>
            {FACTORS.map((f) => (
              <tr key={f.name} className="border-b border-line/50 last:border-0">
                <td className="py-1.5 pr-4 text-slate-200 whitespace-nowrap">{f.name}</td>
                <td className="py-1.5 pr-4 text-signal whitespace-nowrap">up to {f.max}</td>
                <td className="py-1.5 text-muted">{f.what}</td>
              </tr>
            ))}
            <tr>
              <td className="pt-2 pr-4 text-slate-200">Total</td>
              <td className="pt-2 pr-4 text-signal">100</td>
              <td />
            </tr>
          </tbody>
        </table>
      </Panel>

      <Panel title={`Incidents by risk (${ranked.length})`}>
        {loading ? (
          <p className="text-sm text-muted font-mono">Loading…</p>
        ) : ranked.length === 0 ? (
          <p className="text-sm text-muted font-mono">
            No incidents yet. Run a scenario from Demo Mode to generate one.
          </p>
        ) : (
          <ul className="space-y-2">
            {ranked.map((inc) => (
              <li key={inc.incident_id} className="flex items-center gap-3 text-xs font-mono">
                <Link to={`/incidents/${inc.incident_id}`} className="w-24 text-slate-400 hover:text-signal hover:underline">
                  {inc.incident_id}
                </Link>
                <SeverityBadge severity={inc.severity} />
                <span className="flex-1 truncate text-slate-200">{inc.title}</span>
                {inc.risk_score !== null ? (
                  <>
                    <span className="h-1.5 w-40 bg-ink-800 rounded-sm overflow-hidden" aria-hidden>
                      <span
                        className={`block h-full ${riskColor(inc.risk_score)}`}
                        style={{ width: `${Math.min(100, Math.max(0, inc.risk_score))}%` }}
                      />
                    </span>
                    <span className="w-14 text-right text-slate-200">{Math.round(inc.risk_score)}/100</span>
                  </>
                ) : (
                  <span className="text-muted">not scored</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
