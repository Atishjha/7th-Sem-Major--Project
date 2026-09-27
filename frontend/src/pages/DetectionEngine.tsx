import { useEffect, useState } from "react";
import { Panel } from "@/components/ui/panel";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { getRules, updateRule } from "@/services/api";
import type { DetectionRule } from "@/types/event";
export default function DetectionEngine() {
  const { user } = useAuth();
  const canConfigure = user?.role === "ADMIN" || user?.role === "SOC_ANALYST";
  const [rules, setRules] = useState<DetectionRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [drafts, setDrafts] = useState<Record<string, Record<string, string>>>({});
  const [saving, setSaving] = useState<string | null>(null);
  function load() {
    getRules().then((r) => {
      setRules(r);
      const nextDrafts: Record<string, Record<string, string>> = {};
      for (const rule of r) {
        nextDrafts[rule.rule_key] = Object.fromEntries(
          Object.entries(rule.config).map(([k, v]) => [k, String(v)])
        );
      }
      setDrafts(nextDrafts);
      setLoading(false);
    });
  }
  useEffect(load, []);
  async function handleToggle(rule: DetectionRule) {
    setSaving(rule.rule_key);
    try {
      await updateRule(rule.rule_key, { enabled: !rule.enabled });
      load();
    } finally {
      setSaving(null);
    }
  }

  async function handleSaveConfig(rule: DetectionRule) {
    setSaving(rule.rule_key);
    try {
      const draft = drafts[rule.rule_key] ?? {};
      const config: Record<string, number | string> = {};
      for (const [key, value] of Object.entries(draft)) {
        const num = Number(value);
        config[key] = Number.isNaN(num) ? value : num;
      }
      await updateRule(rule.rule_key, { config });
      load();
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">Detection Engine</h1>
        <p className="text-sm text-muted mt-1">
          5 configurable rules, evaluated against every event as it arrives.
        </p>
        {!canConfigure && (
          <p className="text-xs text-severity-medium mt-2">
            Your role ({user?.role}) can view rules but not change them.
          </p>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-muted font-mono">Loading…</p>
      ) : (
        <div className="space-y-4">
          {rules.map((rule) => (
            <Panel
              key={rule.rule_key}
              title={rule.name}
              aside={
                <button
                  onClick={() => handleToggle(rule)}
                  disabled={!canConfigure || saving === rule.rule_key}
                  className={`text-xs px-2 py-1 rounded-sm border ${
                    rule.enabled
                      ? "border-signal/40 text-signal bg-signal/10"
                      : "border-line text-muted"
                  }`}
                >
                  {rule.enabled ? "Enabled" : "Disabled"}
                </button>
              }
            >
              <p className="text-xs text-muted mb-3">{rule.description}</p>
              <div className="flex flex-wrap items-end gap-3">
                {Object.entries(drafts[rule.rule_key] ?? {}).map(([key, value]) => (
                  <div key={key} className="flex flex-col gap-1">
                    <label className="text-[11px] text-muted font-mono">{key}</label>
                    <input
                      value={value}
                      disabled={!canConfigure}
                      onChange={(e) =>
                        setDrafts((prev) => ({
                          ...prev,
                          [rule.rule_key]: { ...prev[rule.rule_key], [key]: e.target.value },
                        }))
                      }
                      className="w-32 rounded-sm border border-line bg-ink-950 px-2 py-1 text-xs font-mono text-slate-100 outline-none focus:ring-2 focus:ring-signal disabled:opacity-50"
                    />
                  </div>
                ))}
                {canConfigure && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={saving === rule.rule_key}
                    onClick={() => handleSaveConfig(rule)}
                  >
                    Save
                  </Button>
                )}
              </div>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}
