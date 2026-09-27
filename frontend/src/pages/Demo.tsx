import { useEffect, useState } from "react";
import { KeyRound, Terminal, Globe2, Network, Layers } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { Button } from "@/components/ui/button";
import { SeverityBadge } from "@/components/SeverityBadge";
import { useAuth } from "@/hooks/useAuth";
import { useEventStream } from "@/hooks/useEventStream";
import * as api from "@/services/api";
import type { ScenarioName, SimulatorStatus } from "@/types/event";

const SCENARIOS: Array<{
  key: ScenarioName;
  title: string;
  description: string;
  icon: typeof KeyRound;
}> = [
  {
    key: "brute_force",
    title: "Brute force",
    description:
      "Repeated failed logins, then a success from an unusual location — the classic account-compromise pattern.",
    icon: KeyRound,
  },
  {
    key: "powershell",
    title: "Suspicious PowerShell",
    description:
      "A normal process launches powershell.exe with a hidden-window flag, matching MITRE T1059.001.",
    icon: Terminal,
  },
  {
    key: "dns_anomaly",
    title: "DNS anomaly",
    description:
      "A burst of high-entropy DNS queries — the kind of pattern seen with DGA-based malware.",
    icon: Globe2,
  },
  {
    key: "network_anomaly",
    title: "Network anomaly",
    description:
      "Normal traffic gives way to a spike in connections and abnormal outbound volume.",
    icon: Network,
  },
  {
    key: "multi_stage",
    title: "Multi-stage incident",
    description:
      "The flagship scenario: brute force → PowerShell → network anomaly, all one continuous chain.",
    icon: Layers,
  },
];

export default function Demo() {
  const { user } = useAuth();
  const canControl = user?.role === "ADMIN" || user?.role === "SOC_ANALYST";
  const { liveEvents, status: wsStatus } = useEventStream();
  const [status, setStatus] = useState<SimulatorStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSimulatorStatus().then(setStatus).catch(() => {});
  }, []);

  useEffect(() => {
    if (wsStatus) setStatus(wsStatus);
  }, [wsStatus]);

  async function handleStart(scenario: ScenarioName) {
    setError(null);
    setBusy(true);
    try {
      const s = await api.startSimulator(scenario);
      setStatus(s);
    } catch (e) {
      setError(e instanceof api.ApiError ? e.message : "Failed to start scenario");
    } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    try {
      const s = await api.stopSimulator();
      setStatus(s);
    } finally {
      setBusy(false);
    }
  }

  const running = status?.running ?? false;
  const progress =
    running && status?.total_events
      ? Math.round((status.events_emitted / status.total_events) * 100)
      : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">Demo Mode</h1>
        <p className="text-sm text-muted mt-1">
          Pick a scenario to generate a synthetic, timed sequence of events —
          streamed live below and stored in the Event Monitor.
        </p>
        {!canControl && (
          <p className="text-xs text-severity-medium mt-2">
            Your role ({user?.role}) can observe scenarios but not start or
            stop them.
          </p>
        )}
      </div>

      {error && <p className="text-sm text-severity-critical">{error}</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SCENARIOS.map(({ key, title, description, icon: Icon }) => (
          <Panel key={key} className="flex flex-col">
            <div className="flex items-start gap-3 mb-3">
              <Icon size={18} className="text-signal mt-0.5" strokeWidth={1.75} />
              <div>
                <h3 className="text-sm font-medium text-slate-100">{title}</h3>
                <p className="text-xs text-muted mt-1">{description}</p>
              </div>
            </div>
            <div className="mt-auto pt-3">
              <Button
                size="sm"
                className="w-full"
                disabled={!canControl || busy || (running && status?.scenario !== key)}
                onClick={() => handleStart(key)}
              >
                {running && status?.scenario === key ? "Running…" : "Start scenario"}
              </Button>
            </div>
          </Panel>
        ))}
      </div>

      <Panel
        title="Scenario status"
        aside={
          running ? (
            <Button size="sm" variant="danger" disabled={!canControl || busy} onClick={handleStop}>
              Stop
            </Button>
          ) : undefined
        }
      >
        {running ? (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-muted font-mono">
              <span>{status?.scenario}</span>
              <span>
                {status?.events_emitted} / {status?.total_events ?? "…"} events
              </span>
            </div>
            <div className="h-1.5 bg-ink-950 rounded-full overflow-hidden">
              <div
                className="h-full bg-signal transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted font-mono">No scenario running.</p>
        )}
      </Panel>

      <Panel title="Live feed">
        {liveEvents.length === 0 ? (
          <p className="text-xs text-muted font-mono">
            Events will appear here as soon as a scenario starts.
          </p>
        ) : (
          <div className="space-y-1.5 font-mono text-xs max-h-72 overflow-y-auto">
            {liveEvents.map((e) => (
              <div key={e.event_id} className="flex items-center gap-2">
                <span className="text-muted whitespace-nowrap">
                  {new Date(e.timestamp).toLocaleTimeString()}
                </span>
                <SeverityBadge severity={e.severity} />
                <span className="text-slate-200">{e.message}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
