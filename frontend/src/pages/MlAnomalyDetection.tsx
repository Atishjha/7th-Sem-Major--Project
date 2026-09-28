import {useEffect,useState} from "react";
import {Panel} from "@/components/ui/panel";
import {Button} from "@/components/ui/button";
import {Badge} from "@/components/ui/badge";
import {useAuth} from "@/hooks/useAuth";
import * as api from "@/services/api";
import type {MLStatus, MLPrediction} from "@/types/ml";
export default function MlAnomalyDetection(){
    const {user}=useAuth();
    const canTrain=user?.role==="ADMIN"||user?.role==="SOC_ANALYST";
    const [status,setStatus]=useState<MLStatus|null>(null);
    const [predictions,setPredictions]=useState<MLPrediction[]>([]);
    const [training,setTraining]=useState(false);
    const [error,setError]=useState<string|null>(null);
    function load(){
        api.getSimulatorStatus().then(setStatus);
        api.getMlPredictions({limit:15,anomalous_only:true}).then(setPredictions);
    }
    useEffect(load,[]);
    async function handleTrain(){
        setError(null);
        setTraining(true);
        try{
            await api.trainMlModel();
            load();
        }catch(e){
            setError(e instanceof api.ApiError?e.message:"Training failed");
        } finally{
            setTraining(false);
        }
    }
    const run = status?.latest_run;
    return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">ML Anomaly Detection</h1>
          <p className="text-sm text-muted mt-1">
            Isolation Forest over 10 behavioral features, computed per source
            IP per 5-minute window.
          </p>
        </div>
        {canTrain && (
          <Button size="sm" disabled={training} onClick={handleTrain}>
            {training ? "Training…" : "Train model"}
          </Button>
        )}
      </div>

      {!canTrain && (
        <p className="text-xs text-severity-medium">
          Your role ({user?.role}) can view model results but not retrain.
        </p>
      )}
      {error && <p className="text-sm text-severity-critical">{error}</p>}

      <Panel title="Model status">
        {!run ? (
          <p className="text-sm text-muted font-mono">
            No model trained yet. {canTrain ? "Click \u201cTrain model\u201d to run the pipeline against current event data." : ""}
          </p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
            <div>
              <div className="text-muted mb-1">Model</div>
              <div className="text-slate-100">{run.model_type}</div>
            </div>
            <div>
              <div className="text-muted mb-1">Version</div>
              <div className="text-slate-100">{run.model_version}</div>
            </div>
            <div>
              <div className="text-muted mb-1">Trained</div>
              <div className="text-slate-100">{new Date(run.trained_at).toLocaleString()}</div>
            </div>
            <div>
              <div className="text-muted mb-1">Samples</div>
              <div className="text-slate-100">{run.num_samples}</div>
            </div>
            <div>
              <div className="text-muted mb-1">Features</div>
              <div className="text-slate-100">{run.num_features}</div>
            </div>
            <div>
              <div className="text-muted mb-1">Contamination</div>
              <div className="text-slate-100">{run.contamination}</div>
            </div>
            <div>
              <div className="text-muted mb-1">Anomalies flagged</div>
              <div className="text-slate-100">{run.anomalies_flagged}</div>
            </div>
            <div>
              <div className="text-muted mb-1">Accuracy</div>
              <Badge tone="neutral">Not Applicable</Badge>
            </div>
            <div className="col-span-2 md:col-span-4">
              <div className="text-muted mb-1">Dataset</div>
              <div className="text-slate-200">{run.training_dataset}</div>
            </div>
            <div className="col-span-2 md:col-span-4">
              <div className="text-muted mb-1">Evaluation</div>
              <div className="text-slate-400">{run.evaluation.note}</div>
            </div>
            <div className="col-span-2 md:col-span-4">
              <div className="text-muted mb-1">Feature set</div>
              <div className="flex flex-wrap gap-1.5">
                {run.feature_names.map((f) => (
                  <Badge key={f} tone="neutral">
                    {f}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        )}
      </Panel>

      <Panel title={`Top anomalous windows (${predictions.length})`}>
        {predictions.length === 0 ? (
          <p className="text-sm text-muted font-mono">
            {run ? "No anomalies flagged in the latest run." : "Train the model to see results here."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-left text-muted border-b border-line">
                  <th className="py-1.5 pr-4">Window</th>
                  <th className="py-1.5 pr-4">Source IP</th>
                  <th className="py-1.5 pr-4">Score</th>
                  <th className="py-1.5 pr-4">Failed logins</th>
                  <th className="py-1.5 pr-4">Bytes sent</th>
                  <th className="py-1.5 pr-4">DNS</th>
                  <th className="py-1.5">Req. frequency</th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((p) => (
                  <tr key={p.id} className="border-b border-line/50">
                    <td className="py-1.5 pr-4 text-muted whitespace-nowrap">
                      {new Date(p.window_start).toLocaleTimeString()}
                    </td>
                    <td className="py-1.5 pr-4 text-slate-300">{p.source_ip}</td>
                    <td className="py-1.5 pr-4 text-severity-high">
                      {p.anomaly_score.toFixed(3)}
                    </td>
                    <td className="py-1.5 pr-4 text-slate-200">
                      {p.features.failed_login_count}
                    </td>
                    <td className="py-1.5 pr-4 text-slate-200">
                      {p.features.bytes_sent.toLocaleString()}
                    </td>
                    <td className="py-1.5 pr-4 text-slate-200">
                      {p.features.dns_request_count}
                    </td>
                    <td className="py-1.5 text-slate-200">{p.features.request_frequency}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}