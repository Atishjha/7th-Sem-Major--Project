# AI Cyber Defense Command Center

An educational, end-semester cybersecurity + AI project: a simplified
AI-powered Security Operations Center (SOC) that collects security
events, detects suspicious behavior with rules and machine learning,
correlates alerts into incidents, explains incidents with an AI
analyst, calculates risk, and recommends safe response actions.

> **Academic Disclaimer**
> This project is an educational cybersecurity demonstration. All live
> events and response actions are simulated. No real systems are
> attacked or modified. All indicators, IPs, usernames, and hostnames
> in the demo data are synthetic.

## Status

This README is being built up phase by phase alongside the code.
Currently complete:

- [x] Phase 1 — Project setup
- [x] Phase 2 — Database + authentication
- [x] Phase 3 — Dashboard
- [x] Phase 4 — Event simulator
- [x] Phase 5 — Rule detection
- [x] Phase 6 — ML anomaly detection
- [x] Phase 7 — Alert correlation
- [x] Phase 8 — Risk engine
- [x] Phase 9 — Incident page
- [x] Phase 10 — AI SOC Analyst (this phase)
- [x] Phase 11 — MITRE ATT&CK
- [x] Phase 12 — Response Center
- [ ] Phase 13 — Audit logs
- [ ] Phase 14 — Dataset / ML training page
- [ ] Phase 15 — Testing
- [ ] Phase 16 — Docker + documentation polish

## Tech Stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui-style
  components, Recharts, Leaflet, Lucide icons
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL
- **ML:** pandas, NumPy, scikit-learn (Isolation Forest)
- **AI:** pluggable provider abstraction (Gemini / Groq / OpenAI-compatible
  / OpenRouter) with a deterministic `MockAIProvider` fallback — the
  app works fully **without any API key**
- **Deployment:** Docker Compose

## Project Structure

See `docs/architecture.md` (added in a later phase) for the full
diagram. Top-level layout:

```text
ai-cyber-defense/
├── frontend/     # React + TS + Vite SPA
├── backend/      # FastAPI application
├── ml/           # training scripts, models, feature engineering
├── data/         # raw / processed / demo datasets (synthetic only)
├── docs/         # architecture, dataset, ML, AI analyst, demo script
├── scripts/      # data generation / seeding / training entrypoints
└── docker-compose.yml
```

## Running it (Phase 1 scope)

Right now, only the skeleton API and a placeholder frontend screen
exist — enough to prove the stack boots end-to-end. Later phases add
the database, detection engine, ML, AI analyst, and the full UI.

### Option A — Docker Compose (recommended once Phase 2+ lands)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend docs (OpenAPI/Swagger): http://localhost:8000/docs
- Backend health check: http://localhost:8000/api/health

### Option B — Run backend locally without Docker

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then visit http://localhost:8000/api/health — you should see:

```json
{
  "status": "ok",
  "service": "AI Cyber Defense Command Center",
  "environment": "development",
  "time": "..."
}
```

### Option C — Run frontend locally without Docker

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 — the placeholder screen will call the
backend's `/api/health` endpoint and show its response.

## Demo Credentials

**DEMO CREDENTIALS — NOT FOR PRODUCTION**

| Username | Password    | Role        |
|----------|-------------|-------------|
| admin    | admin123    | ADMIN       |
| analyst  | analyst123  | SOC_ANALYST |
| viewer   | viewer123   | VIEWER      |

Passwords are hashed with bcrypt before storage — the database never
holds plaintext.

## Database + Auth (Phase 2)

1. Copy the env file and (if not using Docker) point it at a local
   Postgres instance:
   ```bash
   cp .env.example .env
   ```
2. Install backend deps and run migrations:
   ```bash
   cd backend
   pip install -r requirements.txt
   alembic upgrade head
   ```
3. Seed the three demo accounts:
   ```bash
   python ../scripts/seed_demo_data.py
   ```
4. Start the API and log in:
   ```bash
   uvicorn app.main:app --reload
   ```
   ```bash
   curl -X POST http://127.0.0.1:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}'
   ```
   Use the returned `access_token` as a Bearer token against
   `GET /api/auth/me` to confirm the session and role.

RBAC is enforced via a `require_role(...)` FastAPI dependency
(`app/security/dependencies.py`) that later phases attach to
role-restricted endpoints (e.g. only `ADMIN`/`SOC_ANALYST` can approve
response actions in the Response Center).

## Dashboard (Phase 3)

The frontend now has real routing, a login screen, and a protected
app shell with a sidebar covering every module in the spec (most are
"not built yet" placeholders that name the phase that builds them).

The Dashboard page calls the real `GET /api/dashboard` endpoint. Since
the `events`/`alerts`/`incidents` tables don't exist until Phases 4,
5/7, and 9, every KPI and chart is a genuine zero — not a fabricated
placeholder number — with an empty-state message explaining what
populates it and when. The response shape is already final, so later
phases only need to replace the aggregation logic in
`app/services/dashboard_service.py`, not the frontend.

Try it: `docker compose up --build` (or run backend + frontend
locally as above), visit http://localhost:5173, and log in with any
of the demo accounts.

## Event Simulator + Demo Mode (Phase 4)

The `events` table now exists, with a normalized schema matching the
spec exactly (event_id, timestamp, source, source_ip, destination_ip,
username, hostname, event_type, action, status, severity, message,
metadata).

**Seeding:** `scripts/seed_demo_data.py` now also seeds 600 baseline
synthetic events (mostly quiet authentication/DNS/network/endpoint
noise) spread over the last 24 hours, so the Dashboard and Event
Monitor have real data to show even before you run a live scenario.
Re-running the script is safe — it skips seeding if the events table
already has rows.

**The 5 demo scenarios** (Demo Mode page, `/demo`): brute force,
suspicious PowerShell, DNS anomaly, network anomaly, and the
multi-stage flagship (brute force → PowerShell → network anomaly, all
tied to the same synthetic user/host). Every indicator is
deliberately non-resolvable — IPs come from IANA documentation
ranges (RFC 5737), domains use the `.invalid` TLD (RFC 2606), and
"suspicious command" text is a labeled placeholder, never a real
working command line. No scanning, execution, or network activity of
any kind is actually performed — it's just synthetic data written to
the database.

**Real-time delivery:** starting a scenario runs it as a background
task that writes each event to Postgres and immediately broadcasts it
over a WebSocket (`/ws/events`) to every connected client — the
Dashboard's live panel, the Event Monitor table, and the Demo Mode
live feed all update instantly, matching the spec's
Simulator → Backend → Database → WebSocket → Dashboard flow. The
WebSocket is intentionally unauthenticated (it only ever broadcasts
the same synthetic telemetry `GET /api/events` already exposes) — a
known, documented simplification for this academic scope.

**RBAC in action:** `POST /api/simulator/start` and `/stop` require
`ADMIN` or `SOC_ANALYST` — a `VIEWER` gets a `403` and the Demo Mode
UI disables the controls for that role, while still showing the live
feed.

Try it: log in as `analyst`, go to Demo Mode, start "Multi-stage
incident", and watch the events land in the live feed, the Event
Monitor, and the Dashboard's KPI/chart data — all from one real
background job, no fabricated numbers anywhere.

## Rule Detection Engine (Phase 5)

5 configurable rules now run against every event as it's created,
turning matched patterns into real `Alert` rows: **Brute Force**
(≥5 failed logins from one IP in 5 min), **Suspicious PowerShell**
(flagged command pattern), **Impossible Travel** (location change
shortly after a login — approximated via a location-change signal
since there's no real geo-IP dataset in scope here), **DNS Anomaly**
(high query rate from one source), and **Abnormal Network Activity**
(destination count or byte volume over threshold, with a second,
higher threshold that escalates to `critical`).

**Configurable, live:** `GET /api/rules` lists all 5 with their
current thresholds; `POST /api/rules` (ADMIN/SOC_ANALYST only)
updates a rule's config or enabled flag, and it takes effect on the
very next event — no restart needed, since the engine re-reads rule
config from the DB on every run. The Detection Engine page
(`/detection`) exposes this in the UI, with edit controls disabled
for `VIEWER`.

**Debounced, not spammy:** an ongoing brute-force burst produces one
alert, not one per failed login past the threshold — each rule checks
for a recent open alert on the same rule+source before creating a
new one.

**Wired into the real-time pipeline:** each new alert is broadcast
over the same `/ws/events` WebSocket (`{"type": "alert", ...}`) the
moment it's created, so the Alerts page and Dashboard update
instantly during a running scenario — verified through the Vite dev
proxy, not just direct-to-backend.

**Dashboard is now real for detections too:** `critical_alerts`,
`severity_distribution`, and `detection_type_distribution` are
computed from actual `alerts` rows. Everything downstream of ML,
correlation, and incidents (Phases 6–9) still stays a genuine zero.

One known gotcha if you add a new model with a `Severity` column
later (e.g. `Incident` in Phase 9): see the comment in
`app/models/common.py` — Alembic's autogenerated migration needs one
manual tweak (`postgresql.ENUM(..., create_type=False)`) or it will
try to `CREATE TYPE severity` a second time and fail.

## ML Anomaly Detection (Phase 6)

A real Isolation Forest pipeline: Dataset → Cleaning → Feature
Engineering → Scaling → Isolation Forest → Anomaly Score → Anomaly
Classification, exactly as the spec's pipeline diagram describes.

**The 10 features** are exactly the ones the spec names:
`login_frequency`, `failed_login_count`, `request_frequency`,
`bytes_sent`, `bytes_received`, `unique_destination_count`,
`dns_request_count`, `connection_count`, `process_frequency`,
`login_hour` — one feature vector per (source IP, 5-minute window),
computed straight from the `events` table via pandas. Honesty note:
`bytes_received` is currently always 0, since none of our synthetic
scenarios emit inbound byte volume yet — it's included because the
spec names it, not fabricated.

**Never invents accuracy:** this project has no labeled attack/normal
dataset, so every training run reports `accuracy_status:
"not_applicable"` with an explanatory note, exactly per the spec's
"If the dataset does not support accuracy calculation, display
Unsupervised model / Accuracy: Not Applicable" rule. Classification
uses the model's own contamination-based decision boundary
(`IsolationForest.predict`), and the displayed 0–1 anomaly score is a
genuine min-max normalization of `decision_function` output — never a
placeholder number.

**Verified for real, not just plumbing:** trained against 489 real
feature windows accumulated from Phases 4–5's events, correctly
flagged ~5% as anomalous (matching the configured contamination), and
— checked by hand — the highest-scoring windows were exactly the
synthetic attacker IPs (`203.0.113.x`) with high failed-login counts
and multi-hundred-MB `bytes_sent`, not random noise.

**API:** `GET /api/ml/status` (latest run + model metadata),
`POST /api/ml/train` (ADMIN/SOC_ANALYST only — contamination and
window size are configurable per call), `GET /api/ml/predictions`
(recent scored windows, optionally anomalies-only). The model file
itself is persisted under `ml/models/<version>.joblib` via `joblib`.

**Dashboard is now real for ML too:** `anomalies_detected` and the
`ml_anomalies_over_time` chart come from the latest training run's
actual predictions.

The full "Dataset & ML Training" page — CSV/Parquet upload,
preprocess, save-model workflow — is a separate, later feature
(Phase 14); this phase's `/ml` page covers exactly what the spec's
ML Anomaly Detection module (main feature #4) requires: train against
current data and show real, explainable results.

## Alert Correlation (Phase 7)

Multiple alerts now become one **incident**. Every new alert is scored
against each open incident that was active in the last 15 minutes:

| Factor | Weight |
|---|---|
| Shared username | +3 |
| Shared source IP | +3 |
| Shared hostname | +2 |
| Shared destination IP | +2 |
| Last alert within 5 min (temporal proximity) | +1 |
| New kill-chain stage: authentication → endpoint → network (related event type) | +1 |

An alert joins the best-scoring incident that has at least one strong
entity match (user, IP, or host) and a total score of 3 or more;
otherwise it opens a new incident (`INC-1001`, `INC-1002`, …). A
hostname match alone is deliberately not enough, so unrelated activity
that merely touches the same busy server isn't merged. Every alert
belongs to exactly one incident.

**Explainable by construction:** each incident stores the entities seen,
the rules involved, and, per alert, the score and human-readable reasons
it was attached. Expand any row on the Incidents page (`/incidents`) to
see "why these alerts are one incident". Incident type and title are
derived from the rules involved (for example any brute-force or
impossible-travel alert makes it a *Possible Account Compromise*), and
severity is the maximum across its alerts.

**The flagship scenario:** *Multi-stage incident* now trips brute force,
impossible travel, suspicious PowerShell, and abnormal network activity
(four alerts) and correlates them into a single incident. It generates a
fresh synthetic user, host, and IP each run, so rehearsing it twice
gives two clean, separate incidents rather than merging into old ones.

**API:** `GET /api/incidents` (filter by `status`, `severity`) and
`GET /api/incidents/{incident_id}` (the incident, its alerts, and linked
event ids). Incidents also stream over the WebSocket as
`{"type": "incident"}` every time an alert joins one, and the
Dashboard's Active Incidents, Systems at Risk, and Incident timeline are
computed from real incident rows.

**Startup backfill:** on boot the API correlates any alert that has no
incident yet (for example alerts created before this phase), oldest
first. It is idempotent.

Design notes: `incident_events` currently links each incident to the
events that *triggered* its alerts; the Phase 9 timeline can widen this
to every event sharing the incident's entities. `risk_score` is
reserved and stays empty until the Risk Engine (Phase 8). Because the
synthetic pools are small (4 users, 4 hosts, 3 attacker IPs), scenarios
run back-to-back within 15 minutes often share an entity and merge, which
is the correlator doing its job.

## Risk Engine (Phase 8)

Every incident now carries a transparent, capped **0-100 risk score**,
computed from real data — never a random number:

| Factor | Max points | Source |
|---|---|---|
| Severity | 30 | the incident's own severity (max across its alerts) |
| Asset Criticality | 20 | looked up from the new `assets` table by hostname |
| Detection Confidence | 15 | each rule's own `confidence` setting (configurable via `POST /api/rules`, same as its thresholds) |
| Correlated Alerts | 20 | 4 points per alert, capped at 5+ alerts |
| ML Anomaly | 15 | latest Isolation Forest score for a matching source IP, or 0 if there's no match or no model trained yet |

The factors sum to exactly 100 at maximum, so there's no hidden slack.
"Indicator Reputation" from the spec's example is deliberately **not**
one of the factors — there's no threat-intel module in this project,
so rather than fabricate a number for it, it simply isn't scored.

**Asset Criticality is real lookup, not a constant:** 4 hostnames are
seeded by default (`WIN-SRV-DB01` = critical, `WIN-SRV-WEB01` = high,
the two `WIN-CLIENT-0x` = medium). A hostname not in the table — for
example the multi-stage scenario's freshly-generated demo hosts —
falls back to a documented default tier (medium), and the breakdown
says so explicitly rather than hiding it. `GET /api/assets` lists the
table; there's no edit endpoint yet since no page consumes one (adding
one is a natural, low-risk follow-up whenever an Asset Inventory page
is built, since it isn't in the spec's 15 main features by itself).

**Shown visually, not just as a number:** the Incidents page
(`/incidents`) shows the score in the table and, when a row is
expanded, a proportional bar per factor with its point value — the
spec's "Show the calculation visually" requirement.

**Computed live and at startup:** every time a new alert joins or
opens an incident, its risk score is recomputed before the incident is
broadcast over the WebSocket — so it's always current, never stale.
On boot, every existing incident's score is recomputed too (pure
function of current state, so safe to re-run every time).

Verified end-to-end: the DB server incident (critical severity,
critical asset, 5 correlated alerts, a genuine matching ML anomaly)
scored 92/100; an incident on an unregistered host correctly used the
default tier (10 points, not silently 0); every breakdown's points
summed exactly to the reported total.

## Incident Page (Phase 9)

A dedicated `/incidents/:incidentId` page replaces the old inline
expand-in-table view, with the 8 tabs the spec names:

- **Overview** — the risk breakdown (bars, from Phase 8), key facts,
  and the full correlation trail (which alerts, why they're grouped).
- **Timeline** — every linked event in chronological order.
- **Evidence** — the same events as a raw forensic table (ids, IPs,
  host, full JSON metadata).
- **Entities** — the users/IPs/hosts/destinations involved, plus the
  spec's incident graph (User → Source IP → Authentication → Endpoint
  → Process → Network), with only the stages this specific incident's
  events actually touched lit up. A DNS-only incident and the
  multi-stage flagship light up genuinely different stages — it's
  computed from real linked events, not a static diagram.
- **AI Investigation, MITRE ATT&CK, Response, Audit** — honest "not
  built yet" placeholders naming Phases 10–13, same convention used
  for every other not-yet-built area of the app.

**Backend change:** `GET /api/incidents/{id}` now returns the
incident's full linked `events` (chronologically ordered), not just
their ids — Timeline and Evidence need the actual event data to
render. Verified: events are always time-ordered, and every alert's
own triggering events are a confirmed subset of the incident's linked
events, so a Timeline/Evidence tab is never missing anything an alert
reports it relied on.

The Incidents list page (`/incidents`) is now a pure, simpler list —
each row links to its detail page instead of expanding inline. Built
with Radix Tabs (`@radix-ui/react-tabs`, in the dependency list since
Phase 1 but unused until now).

## AI SOC Analyst (Phase 10)

A pluggable AI provider abstraction, with a fully offline, zero-API-key
default — per the spec, the whole demo must work with no key configured.

**`MockAIProvider`** (the default, `AI_PROVIDER=mock`) is deterministic
and data-driven: every sentence in a report is built from real values
pulled out of the incident's own alerts and events (actual IPs,
usernames, byte counts, timestamps, the real risk score) via per-rule
evidence templates and per-incident-type narratives — never generic
placeholder text. Verified against every incident currently in the
database: executive summaries genuinely differ by incident type, every
observed-evidence line traces to a real alert, and the MITRE mapping
and risk explanation reference the incident's actual rules and risk
breakdown.

**The output matches the spec's structure exactly**, with the four
required categories kept as separate, explicit fields rather than
inline tags: Executive Summary, What Happened, Timeline, **Observed
Evidence** (only facts literally present in the data), **Inference**
(interpretation, visually distinguished in the UI with a dashed
border and italics — never merged with evidence), Affected Assets,
Indicators, MITRE ATT&CK Mapping, Risk Explanation, Recommended
Investigation/Containment/Remediation, **Unknown Information** (what
the data genuinely doesn't tell you), and Questions for Human Analyst.

**MITRE mapping** (`app/services/mitre_mapping.py`) uses real, public
ATT&CK technique ids (T1110 Brute Force, T1059.001 PowerShell, T1078
Valid Accounts, T1071.004 DNS, T1041 Exfiltration Over C2) and reuses
each rule's own `confidence` setting from Phase 8 rather than a
separate fabricated number. This module is shared — Phase 11 builds
the dedicated MITRE browsing page on top of the same mapping.

**A real LLM-backed provider** (`app/ai/llm_provider.py`) is also
implemented, for any OpenAI-compatible `/chat/completions` endpoint
(Groq, OpenRouter, or a custom `AI_BASE_URL`). Per the spec — "if an
external LLM is unavailable, the system should still generate a
structured investigation" — any failure (missing config, network
error, bad response) falls back to `MockAIProvider` automatically;
`provider_used` always records which one actually ran (e.g.
`mock (llm_failed: HTTPStatusError)` on a fallback), so a fallback is
never silently indistinguishable from a real call.

**Honesty about what's tested:** `MockAIProvider` is fully tested
end-to-end against real incidents. The LLM provider's *integration
code* — request shape, auth header, JSON-mode parsing, and the
fallback path — was mechanically verified against a local stub server
(3 cases: successful call, server error, and no API key configured —
all passed). It has **not** been exercised against a real LLM backend
in this environment, since no API key is available here. Set
`AI_PROVIDER` / `AI_API_KEY` / `AI_MODEL` (and `AI_BASE_URL` for a
custom `openai_compatible` endpoint) in `.env` to try it for real —
Gemini's native API isn't implemented yet (it doesn't share the
OpenAI chat-completions shape); setting `AI_PROVIDER=gemini` falls
back to Mock with a clear reason rather than crashing.

**API:** `POST /api/incidents/{id}/investigate` (ADMIN/SOC_ANALYST —
always creates a new, timestamped report, so history is preserved)
and `GET /api/incidents/{id}/investigation` (any role — the most
recent report, or `null` if none exists yet). The Incident Page's AI
Investigation tab calls these directly.

