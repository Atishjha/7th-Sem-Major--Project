import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Panel } from "@/components/ui/panel";
import { ResponseActionCard } from "@/components/ResponseActionCard";
import { useAuth } from "@/hooks/useAuth";
import { getAllResponseActions } from "@/services/api";
import type { ResponseAction } from "@/types/response";

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "recommended", label: "Pending review" },
  { value: "simulated_success", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export default function ResponseCenter() {
  const { user } = useAuth();
  const canDecide = user?.role === "ADMIN" || user?.role === "SOC_ANALYST";
  const [actions, setActions] = useState<ResponseAction[] | null>(null);
  const [filter, setFilter] = useState("");

  function load(statusFilter?: string) {
    getAllResponseActions(statusFilter || undefined).then(setActions);
  }

  useEffect(() => load(filter), [filter]);

  const pendingCount = useMemo(
    () => actions?.filter((a) => a.status === "recommended").length ?? 0,
    [actions]
  );

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">Response Center</h1>
        <p className="text-sm text-muted mt-1">
          Every recommended response action across all incidents, in one
          queue. Nothing here ever touches a real system — every approval
          runs a simulated action and records a result, never a live one.
          {pendingCount > 0 && ` ${pendingCount} action(s) pending review.`}
        </p>
        {!canDecide && (
          <p className="text-xs text-severity-medium mt-2">
            Your role ({user?.role}) can view this queue but not approve or reject.
          </p>
        )}
      </div>

      <div className="flex gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`text-xs px-2.5 py-1.5 rounded-sm border ${
              filter === f.value
                ? "border-signal/40 text-signal bg-signal/10"
                : "border-line text-muted hover:text-slate-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <Panel title={`Actions (${actions?.length ?? "…"})`}>
        {actions === null ? (
          <p className="text-sm text-muted font-mono">Loading…</p>
        ) : actions.length === 0 ? (
          <p className="text-sm text-muted font-mono">No actions in this view.</p>
        ) : (
          <div className="space-y-2.5">
            {actions.map((a) => (
              <ResponseActionCard
                key={a.response_id}
                action={a}
                canDecide={canDecide}
                onDecided={(updated) =>
                  setActions((prev) => prev!.map((x) => (x.response_id === updated.response_id ? updated : x)))
                }
              />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
