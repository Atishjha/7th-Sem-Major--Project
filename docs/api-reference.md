# API reference

> **Generated** by `scripts/generate_api_docs.py` from the running application. Do not edit by hand;
> re-run the script after changing a route. Interactive docs are also served at `/docs` (Swagger UI).

All routes live under `/api` and need `Authorization: Bearer <token>` (get one from `POST /api/auth/login`)
unless marked **public**. Roles: **ADMIN**, **SOC_ANALYST** (may change state) and **VIEWER** (read-only).
Access levels below were measured by calling each route as an anonymous user and as a viewer.

**33 HTTP routes + 1 WebSocket.**

## system

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/health` | public | Liveness check: service name, environment and server time. |

## auth

| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | public | Exchange username and password for a JWT (JSON body). |
| `GET` | `/api/auth/me` | any signed-in role | Profile of the signed-in user (never includes the password hash). |

## dashboard

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/dashboard` | any signed-in role | KPIs, charts, recent incidents and live-event feed for the dashboard. |

## events

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/events` | any signed-in role | Raw events, newest first. Filters: `limit`, `source`, `severity`. |

## simulator

| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/simulator/start` | ADMIN, SOC_ANALYST | Start a demo scenario (`brute_force`, `powershell`, `dns_anomaly`, `network_anomaly`, `multi_stage`). 409 if one is already running. |
| `POST` | `/api/simulator/stop` | ADMIN, SOC_ANALYST | Stop the running scenario. |
| `GET` | `/api/simulator/status` | any signed-in role | Whether a scenario is running and how far along it is. |

## alerts

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/alerts` | any signed-in role | Alerts raised by the detection rules. Filters: `limit`, `rule_key`, `severity`. |

## detections

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/detections` | any signed-in role | Same records as alerts, exposed under the name the spec uses. |

## rules

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/rules` | any signed-in role | The detection rules with their live configuration. |
| `POST` | `/api/rules` | ADMIN, SOC_ANALYST | Enable/disable a rule or merge new settings into its config; takes effect immediately and is audited. |

## ml

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/ml/status` | any signed-in role | Whether an event-stream model is trained, plus its latest run (dataset runs are listed under `/api/dataset/runs`). |
| `POST` | `/api/ml/train` | ADMIN, SOC_ANALYST | Train the Isolation Forest on the stored event stream (`contamination` 0-0.5, `window_minutes` 1-1440), then re-score existing incidents with it. Audited. |
| `GET` | `/api/ml/predictions` | any signed-in role | Anomaly scores from the latest run, highest first. Filters: `limit`, `anomalous_only`. |

## incidents

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/incidents` | any signed-in role | Incidents with risk score and breakdown. Filters: `limit`, `status`, `severity`. |
| `GET` | `/api/incidents/{incident_id}` | any signed-in role | One incident with its alerts, evidence events and correlation trail. |
| `POST` | `/api/incidents/{incident_id}/investigate` | ADMIN, SOC_ANALYST | Run the AI SOC analyst on the incident and store the structured report. |
| `GET` | `/api/incidents/{incident_id}/investigation` | any signed-in role | The latest stored investigation, or `null` if none has been run. |
| `GET` | `/api/incidents/{incident_id}/mitre` | any signed-in role | MITRE ATT&CK techniques that apply to this incident, with the rule that evidences each. |
| `GET` | `/api/incidents/{incident_id}/response` | any signed-in role | Recommended response actions for the incident; created on first request, never duplicated. |

## assets

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/assets` | any signed-in role | Registered assets and their criticality (used by the risk engine). |

## mitre

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/mitre/techniques` | any signed-in role | Coverage view: every mapped technique and how much real alert evidence exists for it. |

## response

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/response` | any signed-in role | The global response queue. Filter: `status_filter` (recommended, simulated_success, rejected). |
| `POST` | `/api/response/{response_id}/approve` | ADMIN, SOC_ANALYST | Approve a recommended action. The outcome is simulated and explicitly says nothing real changed. Audited. |
| `POST` | `/api/response/{response_id}/reject` | ADMIN, SOC_ANALYST | Reject a recommended action; no action is taken. Audited. |

## audit

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/audit` | any signed-in role | Append-only audit trail, newest first. Filters: `limit`, `username`, `resource_type`, `resource_id`. |

## dataset

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/dataset/files` | any signed-in role | Raw (uploaded) and processed dataset files. |
| `POST` | `/api/dataset/upload` | ADMIN, SOC_ANALYST | Upload a `.csv` or `.parquet` file (multipart). Other types are rejected. |
| `POST` | `/api/dataset/preprocess` | ADMIN, SOC_ANALYST | Clean a raw file into a numeric feature table (optionally keeping a label column). |
| `POST` | `/api/dataset/train` | ADMIN, SOC_ANALYST | Train on a processed file. Accuracy metrics are computed only if labels are declared. |
| `GET` | `/api/dataset/runs` | any signed-in role | Training runs that came from uploaded datasets. |

## other

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/` | public | Service banner with a pointer to the docs. |

## WebSocket

| Path | Access | Description |
|---|---|---|
| `/ws/events` | public (demo simplification) | Live stream of simulator `event`, `alert`, `incident` and `status` messages. |
