import { useEffect, useRef, useState } from "react";
import { Panel } from "@/components/ui/panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/useAuth";
import * as api from "@/services/api";
import type { DatasetFiles, PreprocessResult, DatasetTrainingRun } from "@/types/dataset";

export default function Dataset() {
  const { user } = useAuth();
  const canManage = user?.role === "ADMIN" || user?.role === "SOC_ANALYST";

  const [files, setFiles] = useState<DatasetFiles | null>(null);
  const [runs, setRuns] = useState<DatasetTrainingRun[] | null>(null);
  const [selectedRaw, setSelectedRaw] = useState<string>("");
  const [labelColumn, setLabelColumn] = useState("");
  const [preprocessResult, setPreprocessResult] = useState<PreprocessResult | null>(null);
  const [attackValues, setAttackValues] = useState("");
  const [contamination, setContamination] = useState("0.05");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function load() {
    api.getDatasetFiles().then(setFiles);
    api.getDatasetRuns().then(setRuns);
  }

  useEffect(load, []);

  async function handleUpload() {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    setError(null);
    setBusy("upload");
    try {
      await api.uploadDataset(file);
      if (fileInputRef.current) fileInputRef.current.value = "";
      load();
    } catch (e) {
      setError(e instanceof api.ApiError ? e.message : "Upload failed");
    } finally {
      setBusy(null);
    }
  }

  async function handlePreprocess() {
    if (!selectedRaw) return;
    setError(null);
    setBusy("preprocess");
    try {
      const result = await api.preprocessDataset(selectedRaw, labelColumn || undefined);
      setPreprocessResult(result);
      load();
    } catch (e) {
      setError(e instanceof api.ApiError ? e.message : "Preprocessing failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleTrain() {
    if (!preprocessResult) return;
    setError(null);
    setBusy("train");
    try {
      await api.trainOnDataset({
        processed_filename: preprocessResult.processed_filename,
        label_column: preprocessResult.label_column || undefined,
        attack_label_values: preprocessResult.label_column
          ? attackValues.split(",").map((s) => s.trim()).filter(Boolean)
          : undefined,
        contamination: parseFloat(contamination) || 0.05,
      });
      load();
    } catch (e) {
      setError(e instanceof api.ApiError ? e.message : "Training failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">Dataset & ML Training</h1>
        <p className="text-sm text-muted mt-1">
          Upload an external CSV/Parquet dataset to train and evaluate an
          Isolation Forest against it. Unlike the ML Anomaly Detection page
          (trained on this project's own unlabeled events), a dataset with a
          label column makes real, computed precision/recall/F1 possible —
          never a placeholder number.
        </p>
        {!canManage && (
          <p className="text-xs text-severity-medium mt-2">
            Your role ({user?.role}) can view datasets and training history
            but not upload, preprocess, or train.
          </p>
        )}
      </div>

      {error && <p className="text-sm text-severity-critical">{error}</p>}

      {canManage && (
        <Panel title="1. Load dataset">
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.parquet"
              className="text-xs text-muted file:mr-3 file:rounded-sm file:border file:border-line file:bg-ink-800 file:px-3 file:py-1.5 file:text-slate-200 file:text-xs"
            />
            <Button size="sm" disabled={busy === "upload"} onClick={handleUpload}>
              {busy === "upload" ? "Uploading…" : "Upload"}
            </Button>
          </div>
        </Panel>
      )}

      <Panel title="Raw files">
        {!files || files.raw.length === 0 ? (
          <p className="text-xs text-muted font-mono">No files in data/raw/ yet.</p>
        ) : (
          <div className="space-y-1.5">
            {files.raw.map((f) => (
              <label
                key={f.filename}
                className="flex items-center gap-2 text-xs font-mono text-slate-300 cursor-pointer"
              >
                <input
                  type="radio"
                  name="raw-file"
                  checked={selectedRaw === f.filename}
                  onChange={() => setSelectedRaw(f.filename)}
                />
                {f.filename}
                <span className="text-muted">({(f.size_bytes / 1024).toFixed(1)} KB)</span>
              </label>
            ))}
          </div>
        )}
      </Panel>

      {canManage && selectedRaw && (
        <Panel title="2. Preprocess">
          <div className="flex items-end gap-3 flex-wrap">
            <div className="flex flex-col gap-1">
              <label className="text-[11px] text-muted font-mono">
                Label column (optional — enables real evaluation)
              </label>
              <input
                value={labelColumn}
                onChange={(e) => setLabelColumn(e.target.value)}
                placeholder="e.g. label"
                className="w-48 rounded-sm border border-line bg-ink-950 px-2 py-1 text-xs font-mono text-slate-100"
              />
            </div>
            <Button size="sm" disabled={busy === "preprocess"} onClick={handlePreprocess}>
              {busy === "preprocess" ? "Preprocessing…" : "Preprocess"}
            </Button>
          </div>

          {preprocessResult && (
            <div className="mt-3 text-xs font-mono text-slate-300 space-y-1">
              <div>Processed file: {preprocessResult.processed_filename}</div>
              <div>Records: {preprocessResult.num_records}</div>
              <div>Features: {preprocessResult.feature_names.join(", ")}</div>
              {preprocessResult.dropped_columns.length > 0 && (
                <div className="text-muted">
                  Dropped (non-numeric): {preprocessResult.dropped_columns.join(", ")}
                </div>
              )}
              {preprocessResult.label_distribution && (
                <div>
                  Label distribution:{" "}
                  {Object.entries(preprocessResult.label_distribution)
                    .map(([k, v]) => `${k}=${v}`)
                    .join(", ")}
                </div>
              )}
            </div>
          )}
        </Panel>
      )}

      {canManage && preprocessResult && (
        <Panel title="3. Train & evaluate">
          <div className="flex items-end gap-3 flex-wrap">
            {preprocessResult.label_column && (
              <div className="flex flex-col gap-1">
                <label className="text-[11px] text-muted font-mono">
                  Attack label value(s), comma-separated
                </label>
                <input
                  value={attackValues}
                  onChange={(e) => setAttackValues(e.target.value)}
                  placeholder="e.g. attack,malicious"
                  className="w-56 rounded-sm border border-line bg-ink-950 px-2 py-1 text-xs font-mono text-slate-100"
                />
              </div>
            )}
            <div className="flex flex-col gap-1">
              <label className="text-[11px] text-muted font-mono">Contamination</label>
              <input
                value={contamination}
                onChange={(e) => setContamination(e.target.value)}
                className="w-24 rounded-sm border border-line bg-ink-950 px-2 py-1 text-xs font-mono text-slate-100"
              />
            </div>
            <Button size="sm" disabled={busy === "train"} onClick={handleTrain}>
              {busy === "train" ? "Training…" : "Train & evaluate"}
            </Button>
          </div>
          <p className="text-xs text-muted mt-2">
            Training, evaluation, and saving the model happen as one step —
            there's nothing meaningful for a separate "Evaluate" or "Save"
            click to do beyond what training already does.
          </p>
        </Panel>
      )}

      <Panel title={`Training history (${runs?.length ?? "…"})`}>
        {!runs || runs.length === 0 ? (
          <p className="text-sm text-muted font-mono">No dataset training runs yet.</p>
        ) : (
          <div className="space-y-3">
            {runs.map((r) => (
              <div key={r.id} className="border border-line rounded-sm p-3 text-xs font-mono">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <span className="text-slate-200">{r.model_version}</span>
                    <span className="text-muted ml-2">({r.dataset_filename})</span>
                  </div>
                  <Badge tone={r.accuracy_status === "computed" ? "signal" : "neutral"}>
                    {r.accuracy_status === "computed" ? "Accuracy: computed" : "Accuracy: Not Applicable"}
                  </Badge>
                </div>
                <div className="mt-1.5 text-slate-400">
                  Samples: {r.num_samples} | Features: {r.num_features} | Anomalies flagged:{" "}
                  {r.anomalies_flagged} | Trained: {new Date(r.trained_at).toLocaleString()}
                </div>
                {r.accuracy_status === "computed" && (
                  <div className="mt-1.5 text-slate-300">
                    accuracy={r.evaluation.accuracy} precision={r.evaluation.precision} recall=
                    {r.evaluation.recall} f1={r.evaluation.f1} — TP={r.evaluation.true_positives} FP=
                    {r.evaluation.false_positives} TN={r.evaluation.true_negatives} FN=
                    {r.evaluation.false_negatives}
                  </div>
                )}
                {r.evaluation.note && <div className="mt-1 text-muted italic">{r.evaluation.note}</div>}
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
