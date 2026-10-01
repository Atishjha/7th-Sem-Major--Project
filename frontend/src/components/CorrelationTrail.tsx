import { SeverityBadge } from "@/components/SeverityBadge";
import type { Alert } from "@/types/event";
import type { CorrelationEntry } from "@/types/incident";

export function CorrelationTrail({
  alerts,
  trail,
}: {
  alerts: Alert[];
  trail?: CorrelationEntry[];
}) {
  return (
    <div className="space-y-2.5">
      {alerts.map((a) => {
        const entry = trail?.find((t) => t.alert_id === a.alert_id);
        return (
          <div key={a.alert_id} className="flex gap-3 text-xs">
            <span className="text-muted whitespace-nowrap pt-0.5 font-mono">
              {new Date(a.detected_at).toLocaleTimeString()}
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-slate-400 font-mono">{a.alert_id}</span>
                <SeverityBadge severity={a.severity} />
                <span className="text-signal">{a.rule_name}</span>
              </div>
              <div className="text-slate-400 mt-0.5">
                {entry && entry.score > 0
                  ? `score ${entry.score}: ${entry.reasons.join("; ")}`
                  : "first alert — opened this incident"}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
