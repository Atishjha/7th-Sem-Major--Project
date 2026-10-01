import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/SeverityBadge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { RiskBreakdown } from "@/components/RiskBreakdown";
import { CorrelationTrail } from "@/components/CorrelationTrail";
import { IncidentGraph } from "@/components/IncidentGraph";
import { useEventStream } from "@/hooks/useEventStream";
import { getIncident } from "@/services/api";
import type { IncidentDetail as IncidentDetailType } from "@/types/incident";

const ENTITY_LABELS: Record<string, string> = {
  usernames: "Users",
  source_ips: "Source IPs",
  hostnames: "Hosts",
  destination_ips: "Destinations",
};

function NotBuiltYet({ phase }: { phase: string }) {
  return (
    <Panel className="text-center py-12">
      <p className="text-sm text-muted">This tab isn't built yet — {phase}.</p>
    </Panel>
  );
}

export default function IncidentDetail() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const [incident, setIncident] = useState<IncidentDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { liveIncidents } = useEventStream();

  function load() {
    if (!incidentId) return;
    getIncident(incidentId)
      .then(setIncident)
      .catch(() => setError(`No incident '${incidentId}'`));
  }

  useEffect(load, [incidentId]);

  // keep it current while a running scenario keeps adding alerts to it
  useEffect(() => {
    if (incident && liveIncidents.some((i) => i.incident_id === incident.incident_id)) {
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveIncidents]);

  if (error) {
    return (
      <div className="space-y-4">
        <Link to="/incidents" className="text-sm text-signal hover:underline inline-flex items-center gap-1">
          <ArrowLeft size={14} /> Back to incidents
        </Link>
        <Panel>
          <p className="text-sm text-severity-critical">{error}</p>
        </Panel>
      </div>
    );
  }

  if (!incident) {
    return <p className="text-sm text-muted font-mono">Loading…</p>;
  }

  const entities = incident.incident_metadata.entities ?? {};

  return (
    <div className="space-y-4">
      <Link to="/incidents" className="text-sm text-signal hover:underline inline-flex items-center gap-1">
        <ArrowLeft size={14} /> Back to incidents
      </Link>

      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-muted font-mono text-sm">{incident.incident_id}</span>
            <SeverityBadge severity={incident.severity} />
            <Badge tone="neutral">{incident.status}</Badge>
          </div>
          <h1 className="text-lg font-semibold text-slate-100 mt-1">{incident.title}</h1>
        </div>
        <div className="text-right">
          <div className="text-xs text-muted">Risk score</div>
          <div className="text-2xl font-mono text-slate-100">
            {incident.risk_score !== null ? Math.round(incident.risk_score) : "—"}/100
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="evidence">Evidence</TabsTrigger>
          <TabsTrigger value="entities">Entities</TabsTrigger>
          <TabsTrigger value="ai">AI Investigation</TabsTrigger>
          <TabsTrigger value="mitre">MITRE ATT&CK</TabsTrigger>
          <TabsTrigger value="response">Response</TabsTrigger>
          <TabsTrigger value="audit">Audit</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Panel title="Risk breakdown">
              <RiskBreakdown
                riskScore={incident.risk_score}
                breakdown={incident.incident_metadata.risk_breakdown}
              />
            </Panel>
            <Panel title="Summary">
              <dl className="grid grid-cols-2 gap-y-2 text-xs font-mono">
                <dt className="text-muted">Incident type</dt>
                <dd className="text-slate-200">{incident.incident_type}</dd>
                <dt className="text-muted">First seen</dt>
                <dd className="text-slate-200">{new Date(incident.first_seen).toLocaleString()}</dd>
                <dt className="text-muted">Last seen</dt>
                <dd className="text-slate-200">{new Date(incident.last_seen).toLocaleString()}</dd>
                <dt className="text-muted">Alerts</dt>
                <dd className="text-slate-200">{incident.alert_count}</dd>
                <dt className="text-muted">Primary user</dt>
                <dd className="text-slate-200">{incident.primary_username ?? "—"}</dd>
                <dt className="text-muted">Primary source IP</dt>
                <dd className="text-slate-200">{incident.primary_source_ip ?? "—"}</dd>
                <dt className="text-muted">Primary host</dt>
                <dd className="text-slate-200">{incident.primary_hostname ?? "—"}</dd>
              </dl>
            </Panel>
          </div>
          <Panel title={`Alerts (${incident.alerts.length})`}>
            <CorrelationTrail
              alerts={incident.alerts}
              trail={incident.incident_metadata.correlation}
            />
          </Panel>
        </TabsContent>

        <TabsContent value="timeline">
          <Panel title={`Timeline (${incident.events.length} events)`}>
            {incident.events.length === 0 ? (
              <p className="text-sm text-muted font-mono">No linked events.</p>
            ) : (
              <div className="space-y-2.5 max-h-[32rem] overflow-y-auto">
                {incident.events.map((e) => (
                  <div key={e.id} className="flex gap-3 text-xs">
                    <span className="text-muted whitespace-nowrap pt-0.5 font-mono">
                      {new Date(e.timestamp).toLocaleTimeString()}
                    </span>
                    <SeverityBadge severity={e.severity} />
                    <span className="text-signal font-mono">{e.source}</span>
                    <span className="text-slate-200">{e.message}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </TabsContent>

        <TabsContent value="evidence">
          <Panel title="Raw event evidence">
            {incident.events.length === 0 ? (
              <p className="text-sm text-muted font-mono">No linked events.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr className="text-left text-muted border-b border-line">
                      <th className="py-1.5 pr-4">Event ID</th>
                      <th className="py-1.5 pr-4">Timestamp</th>
                      <th className="py-1.5 pr-4">Type</th>
                      <th className="py-1.5 pr-4">Source IP</th>
                      <th className="py-1.5 pr-4">Dest IP</th>
                      <th className="py-1.5 pr-4">Host</th>
                      <th className="py-1.5">Metadata</th>
                    </tr>
                  </thead>
                  <tbody>
                    {incident.events.map((e) => (
                      <tr key={e.id} className="border-b border-line/50 align-top">
                        <td className="py-1.5 pr-4 text-muted">{e.event_id}</td>
                        <td className="py-1.5 pr-4 text-muted whitespace-nowrap">
                          {new Date(e.timestamp).toISOString()}
                        </td>
                        <td className="py-1.5 pr-4 text-slate-200">{e.event_type}</td>
                        <td className="py-1.5 pr-4 text-slate-400">{e.source_ip ?? "—"}</td>
                        <td className="py-1.5 pr-4 text-slate-400">{e.destination_ip ?? "—"}</td>
                        <td className="py-1.5 pr-4 text-slate-400">{e.hostname ?? "—"}</td>
                        <td className="py-1.5 text-slate-500 max-w-xs truncate">
                          {JSON.stringify(e.event_metadata)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </TabsContent>

        <TabsContent value="entities" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Panel title="Entities involved">
              <div className="space-y-3">
                {Object.entries(entities).map(([key, values]) =>
                  values && values.length > 0 ? (
                    <div key={key}>
                      <div className="text-xs text-muted mb-1">{ENTITY_LABELS[key] ?? key}</div>
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
                {Object.values(entities).every((v) => !v || v.length === 0) && (
                  <p className="text-sm text-muted font-mono">No entities recorded.</p>
                )}
              </div>
            </Panel>
            <Panel title="Incident graph">
              <IncidentGraph
                primaryUsername={incident.primary_username}
                primarySourceIp={incident.primary_source_ip}
                events={incident.events}
              />
            </Panel>
          </div>
        </TabsContent>

        <TabsContent value="ai">
          <NotBuiltYet phase="the AI SOC Analyst lands in Phase 10" />
        </TabsContent>
        <TabsContent value="mitre">
          <NotBuiltYet phase="MITRE ATT&CK mapping lands in Phase 11" />
        </TabsContent>
        <TabsContent value="response">
          <NotBuiltYet phase="the Response Center lands in Phase 12" />
        </TabsContent>
        <TabsContent value="audit">
          <NotBuiltYet phase="audit logging lands in Phase 13" />
        </TabsContent>
      </Tabs>
    </div>
  );
}
