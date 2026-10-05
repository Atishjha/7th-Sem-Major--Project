import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Panel } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { getMitreTechniques } from "@/services/api";
import type { TechniqueObservation } from "@/types/mitre";

export default function MitreAttack() {
  const [techniques, setTechniques] = useState<TechniqueObservation[] | null>(null);

  useEffect(() => {
    getMitreTechniques().then(setTechniques);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">MITRE ATT&CK</h1>
        <p className="text-sm text-muted mt-1">
          Every technique this project's detection rules can map to, each
          marked with its real observation history — a rule that has never
          fired shows no fabricated evidence, just an honest "not yet
          observed". For educational defensive analysis only.
        </p>
      </div>

      <Panel title={`Techniques (${techniques?.length ?? "…"})`}>
        {techniques === null ? (
          <p className="text-sm text-muted font-mono">Loading…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-left text-muted border-b border-line">
                  <th className="py-1.5 pr-4">Technique</th>
                  <th className="py-1.5 pr-4">ID</th>
                  <th className="py-1.5 pr-4">Tactic</th>
                  <th className="py-1.5 pr-4">Confidence</th>
                  <th className="py-1.5 pr-4">Alerts</th>
                  <th className="py-1.5 pr-4">Incidents</th>
                  <th className="py-1.5 pr-4">Last seen</th>
                  <th className="py-1.5">Evidence</th>
                </tr>
              </thead>
              <tbody>
                {techniques.map((t) => {
                  const observed = t.alert_count > 0;
                  return (
                    <tr
                      key={t.technique_id}
                      className={`border-b border-line/50 ${!observed ? "opacity-50" : ""}`}
                    >
                      <td className="py-1.5 pr-4 text-slate-200">{t.technique_name}</td>
                      <td className="py-1.5 pr-4 text-signal">{t.technique_id}</td>
                      <td className="py-1.5 pr-4 text-slate-400">{t.tactic}</td>
                      <td className="py-1.5 pr-4 text-muted">{t.confidence}</td>
                      <td className="py-1.5 pr-4 text-slate-200">{t.alert_count}</td>
                      <td className="py-1.5 pr-4 text-slate-200">{t.incident_count}</td>
                      <td className="py-1.5 pr-4 text-muted whitespace-nowrap">
                        {t.last_seen ? new Date(t.last_seen).toLocaleString() : "—"}
                      </td>
                      <td className="py-1.5">
                        {observed ? (
                          <div className="flex flex-wrap gap-1">
                            {t.evidence_incident_ids.map((iid) => (
                              <Link key={iid} to={`/incidents/${iid}`}>
                                <Badge tone="signal" className="hover:underline cursor-pointer">
                                  {iid}
                                </Badge>
                              </Link>
                            ))}
                          </div>
                        ) : (
                          <span className="text-muted italic">not yet observed</span>
                        )}
                      </td>
                    </tr>
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
