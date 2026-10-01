import type { RiskFactor } from "@/types/incident";

export function RiskBreakdown({
  riskScore,
  breakdown,
}: {
  riskScore: number | null;
  breakdown?: RiskFactor[];
}) {
  if (!breakdown) {
    return <p className="text-sm text-muted font-mono">Not yet scored.</p>;
  }
  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span className="text-muted text-sm">Risk score</span>
        <span className="text-2xl font-mono text-slate-100">
          {Math.round(riskScore ?? 0)}/100
        </span>
      </div>
      <div className="space-y-1.5">
        {breakdown.map((f) => (
          <div key={f.factor} className="flex items-center gap-3 text-xs">
            <span className="w-40 shrink-0 text-slate-300">{f.label}</span>
            <div className="flex-1 h-2 bg-ink-950 rounded-full overflow-hidden">
              <div
                className="h-full bg-signal"
                style={{ width: `${(f.points / f.max_points) * 100}%` }}
              />
            </div>
            <span className="w-16 text-right font-mono text-slate-200">
              +{f.points}/{f.max_points}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
