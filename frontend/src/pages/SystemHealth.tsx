import { useCallback, useEffect, useState } from "react";
import { Panel } from "@/components/ui/panel";
import { Badge } from "@/components/ui/badge";
import { getAiStatus, getHealth, getMlStatus, getSimulatorStatus } from "@/services/api";
import type { AiStatus, HealthResponse } from "@/services/api";
import type { MLStatus } from "@/types/ml";
import type { SimulatorStatus } from "@/types/event";

const REFRESH_MS = 10_000;

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-line/50 last:border-0 text-xs font-mono">
      <span className="text-muted">{label}</span>
      <span className="text-slate-200">{children}</span>
    </div>
  );
}

export default function SystemHealth() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [ml, setMl] = useState<MLStatus | null>(null);
  const [sim, setSim] = useState<SimulatorStatus | null>(null);
  const [ai, setAi] = useState<AiStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [h, m, s, a] = await Promise.all([getHealth(), getMlStatus(), getSimulatorStatus(), getAiStatus()]);
      setHealth(h);
      setMl(m);
      setSim(s);
      setAi(a);
      setError(null);
    } catch (e) {
      setHealth(null);
      setError(e instanceof Error ? e.message : "Backend unreachable");
    } finally {
      setCheckedAt(new Date());
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const up = health?.status === "ok";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">System Health</h1>
          <p className="text-sm text-muted mt-1">
            Live status of the services behind this console. Refreshes every 10 seconds.
          </p>
        </div>
        <button
          onClick={refresh}
          className="rounded-sm border border-line px-3 py-1.5 text-xs text-slate-300 hover:border-signal/50"
        >
          Refresh now
        </button>
      </div>

      {error && (
        <Panel className="border-severity-critical/40">
          <p role="alert" className="text-sm text-severity-critical">
            Backend unreachable: {error}
          </p>
        </Panel>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Panel title="Backend API">
          <div className="px-4 py-2">
            <Row label="Status">
              <Badge tone={up ? "signal" : "critical"}>{up ? "healthy" : "down"}</Badge>
            </Row>
            <Row label="Service">{health?.service ?? "—"}</Row>
            <Row label="Environment">{health?.environment ?? "—"}</Row>
            <Row label="Server time">{health ? new Date(health.time).toLocaleTimeString() : "—"}</Row>
          </div>
        </Panel>

        <Panel title="ML model">
          <div className="px-4 py-2">
            <Row label="Model">
              {ml ? (
                <Badge tone={ml.has_model ? "signal" : "neutral"}>{ml.has_model ? "trained" : "not trained"}</Badge>
              ) : (
                "—"
              )}
            </Row>
            <Row label="Version">{ml?.latest_run?.model_version ?? "—"}</Row>
            <Row label="Samples">{ml?.latest_run?.num_samples ?? "—"}</Row>
            <Row label="Accuracy">
              {ml?.latest_run
                ? ml.latest_run.accuracy_status === "computed"
                  ? "computed from labels"
                  : "not applicable (no labels)"
                : "—"}
            </Row>
          </div>
        </Panel>

        <Panel title="AI analyst">
          <div className="px-4 py-2">
            <Row label="Answering">
              {ai ? <Badge tone={ai.mode === "live" ? "signal" : "neutral"}>{ai.mode === "live" ? "live model" : "offline mock"}</Badge> : "—"}
            </Row>
            <Row label="Provider">{ai?.provider ?? "—"}</Row>
            <Row label="Model">{ai?.model ?? "—"}</Row>
            <Row label="API key">{ai ? (ai.key_configured ? "set" : "not set") : "—"}</Row>
            {ai?.note && <p className="pt-2 text-xs text-muted">{ai.note}</p>}
          </div>
        </Panel>

        <Panel title="Event simulator">
          <div className="px-4 py-2">
            <Row label="State">
              {sim ? <Badge tone={sim.running ? "signal" : "neutral"}>{sim.running ? "running" : "idle"}</Badge> : "—"}
            </Row>
            <Row label="Scenario">{sim?.scenario ?? "—"}</Row>
            <Row label="Events emitted">{sim ? sim.events_emitted : "—"}</Row>
          </div>
        </Panel>
      </div>

      <p className="text-xs text-muted font-mono">
        Last checked: {checkedAt ? checkedAt.toLocaleTimeString() : "…"}
      </p>
    </div>
  );
}
