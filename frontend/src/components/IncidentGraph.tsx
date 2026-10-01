import { ArrowDown } from "lucide-react";
import type { SocEvent } from "@/types/event";

interface IncidentGraphProps {
  primaryUsername: string | null;
  primarySourceIp: string | null;
  events: SocEvent[];
}

/**
 * The spec's incident graph: User -> Source IP -> Authentication ->
 * Endpoint -> Process -> Network. Each node is lit up only if this
 * specific incident's actual linked events touch that stage — a
 * DNS-anomaly-only incident shows a very different lit path than the
 * multi-stage account-compromise flagship, because the data is real.
 */
export function IncidentGraph({ primaryUsername, primarySourceIp, events }: IncidentGraphProps) {
  const has = (pred: (e: SocEvent) => boolean) => events.some(pred);

  const nodes = [
    { label: "User", detail: primaryUsername, present: !!primaryUsername },
    { label: "Source IP", detail: primarySourceIp, present: !!primarySourceIp },
    {
      label: "Authentication",
      detail: null,
      present: has((e) => e.source === "authentication"),
    },
    { label: "Endpoint", detail: null, present: has((e) => e.source === "endpoint") },
    {
      label: "Process",
      detail: null,
      present: has((e) => e.event_type === "process_execution"),
    },
    {
      label: "Network",
      detail: null,
      present: has((e) => e.source === "network" || e.source === "dns"),
    },
  ];

  return (
    <div className="flex flex-col items-start gap-1.5">
      {nodes.map((node, i) => (
        <div key={node.label} className="flex flex-col items-start">
          <div
            className={`rounded-sm border px-3 py-1.5 text-xs font-mono ${
              node.present
                ? "border-signal/50 bg-signal/10 text-signal"
                : "border-line text-muted"
            }`}
          >
            {node.label}
            {node.detail && <span className="text-slate-300 ml-2">{node.detail}</span>}
          </div>
          {i < nodes.length - 1 && (
            <ArrowDown
              size={14}
              className={node.present ? "text-signal/50 my-1 ml-3" : "text-line my-1 ml-3"}
            />
          )}
        </div>
      ))}
    </div>
  );
}
