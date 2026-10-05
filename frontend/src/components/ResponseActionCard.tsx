import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import * as api from "@/services/api";
import type { ResponseAction } from "@/types/response";

const STATUS_TONE: Record<string, "medium" | "signal" | "neutral"> = {
  recommended: "medium",
  simulated_success: "signal",
  rejected: "neutral",
};

export function ResponseActionCard({
  action,
  canDecide,
  onDecided,
  showIncidentLink,
}: {
  action: ResponseAction;
  canDecide: boolean;
  onDecided: (updated: ResponseAction) => void;
  showIncidentLink?: React.ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function decide(fn: (id: string) => Promise<ResponseAction>) {
    setBusy(true);
    setError(null);
    try {
      onDecided(await fn(action.response_id));
    } catch (e) {
      setError(e instanceof api.ApiError ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border border-line rounded-sm p-3 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-muted">{action.response_id}</span>
            <span className="text-sm text-slate-100">{action.action_label}</span>
            <span className="text-xs text-signal font-mono">{action.target}</span>
            <Badge tone={STATUS_TONE[action.status]}>{action.status.replace("_", " ")}</Badge>
            {showIncidentLink}
          </div>
          <p className="text-xs text-muted mt-1">{action.recommended_reason}</p>
        </div>

        {action.status === "recommended" && canDecide && (
          <div className="flex gap-2 shrink-0">
            <Button size="sm" variant="outline" disabled={busy} onClick={() => decide(api.rejectResponseAction)}>
              Reject
            </Button>
            <Button size="sm" disabled={busy} onClick={() => decide(api.approveResponseAction)}>
              Approve
            </Button>
          </div>
        )}
      </div>

      {error && <p className="text-xs text-severity-critical">{error}</p>}

      {action.result_message && (
        <p className="text-xs font-mono text-slate-300 bg-ink-950 rounded-sm px-2 py-1.5">
          {action.result_message}
          {action.decided_by_username && (
            <span className="text-muted"> — decided by {action.decided_by_username}</span>
          )}
        </p>
      )}
    </div>
  );
}
