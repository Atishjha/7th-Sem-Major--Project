import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Panel } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { getAuditLogs } from "@/services/api";
import type { AuditLogEntry } from "@/types/audit";

const RESOURCE_TYPES = ["", "incident", "detection_rule", "simulator"];

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLogEntry[] | null>(null);
  const [resourceType, setResourceType] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    getAuditLogs({ limit: 200, resource_type: resourceType || undefined }).then(setLogs);
  }, [resourceType]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">Audit Logs</h1>
        <p className="text-sm text-muted mt-1">
          Every privileged, state-changing action in the system — starting a
          scenario, editing a detection rule, running an AI investigation,
          approving or rejecting a response action.
        </p>
      </div>

      <div className="flex gap-2">
        {RESOURCE_TYPES.map((rt) => (
          <button
            key={rt}
            onClick={() => setResourceType(rt)}
            className={`text-xs px-2.5 py-1.5 rounded-sm border ${
              resourceType === rt
                ? "border-signal/40 text-signal bg-signal/10"
                : "border-line text-muted hover:text-slate-200"
            }`}
          >
            {rt || "All"}
          </button>
        ))}
      </div>

      <Panel title={`Entries (${logs?.length ?? "…"})`}>
        {logs === null ? (
          <p className="text-sm text-muted font-mono">Loading…</p>
        ) : logs.length === 0 ? (
          <p className="text-sm text-muted font-mono">No audit entries in this view.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-left text-muted border-b border-line">
                  <th className="py-1.5 pr-4">Time</th>
                  <th className="py-1.5 pr-4">User</th>
                  <th className="py-1.5 pr-4">Action</th>
                  <th className="py-1.5 pr-4">Resource</th>
                  <th className="py-1.5">Result</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((e) => (
                  <Fragment key={e.id}>
                    <tr
                      onClick={() => setExpanded(expanded === e.id ? null : e.id)}
                      className="border-b border-line/50 cursor-pointer hover:bg-ink-800/40"
                    >
                      <td className="py-1.5 pr-4 text-muted whitespace-nowrap">
                        {new Date(e.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="py-1.5 pr-4 text-slate-300">{e.username}</td>
                      <td className="py-1.5 pr-4 text-slate-200">{e.action}</td>
                      <td className="py-1.5 pr-4 text-signal">
                        {e.resource_type === "incident" && e.resource_id ? (
                          <Link
                            to={`/incidents/${e.resource_id}`}
                            onClick={(ev) => ev.stopPropagation()}
                            className="hover:underline"
                          >
                            {e.resource_id}
                          </Link>
                        ) : (
                          <span>
                            {e.resource_type}
                            {e.resource_id ? `:${e.resource_id}` : ""}
                          </span>
                        )}
                      </td>
                      <td className="py-1.5">
                        <Badge tone={e.result === "SUCCESS" ? "signal" : "critical"}>{e.result}</Badge>
                      </td>
                    </tr>
                    {expanded === e.id && (e.old_value || e.new_value) && (
                      <tr className="border-b border-line/50 bg-ink-950/60">
                        <td colSpan={5} className="px-4 py-3">
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <div className="text-muted mb-1">Old value</div>
                              <pre className="text-slate-400 whitespace-pre-wrap">
                                {e.old_value ? JSON.stringify(e.old_value, null, 2) : "—"}
                              </pre>
                            </div>
                            <div>
                              <div className="text-muted mb-1">New value</div>
                              <pre className="text-slate-300 whitespace-pre-wrap">
                                {e.new_value ? JSON.stringify(e.new_value, null, 2) : "—"}
                              </pre>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
