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

All 17 phases are complete.

- [x] Phase 1 — Project setup
- [x] Phase 2 — Database + authentication
- [x] Phase 3 — Dashboard
- [x] Phase 4 — Event simulator
- [x] Phase 5 — Rule detection
- [x] Phase 6 — ML anomaly detection
- [x] Phase 7 — Alert correlation
- [x] Phase 8 — Risk engine
- [x] Phase 9 — Incident page
- [x] Phase 10 — AI SOC Analyst
- [x] Phase 11 — MITRE ATT&CK
- [x] Phase 12 — Response Center
- [x] Phase 13 — Audit logs
- [x] Phase 14 — Dataset / ML training page
- [x] Phase 15 — Testing
- [x] Phase 16 — Docker + documentation polish
- [x] Phase 17 — Real AI model connection (this phase)

## What it does

1. **Collects** synthetic security events (a built-in simulator with five attack scenarios, plus 600 baseline events).
2. **Detects** with five configurable rules and an Isolation Forest anomaly model.
3. **Correlates** alerts into incidents and explains *why* each alert joined.
4. **Scores** every incident 0-100 from five inspectable factors.
5. **Explains** incidents with an AI SOC analyst that works offline and never fails to answer.
6. **Maps** detections to MITRE ATT&CK techniques.
7. **Recommends** response actions that an analyst approves or rejects. Outcomes are simulated; nothing real is touched.
8. **Records** every privileged action in an append-only audit log.

## Tech Stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui-style components, Recharts, Leaflet, Lucide icons
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL
- **ML:** pandas, NumPy, scikit-learn (Isolation Forest)
- **AI:** pluggable provider abstraction (Groq, OpenRouter, or any OpenAI-compatible endpoint) with a deterministic
  `MockAIProvider` fallback, so the app works fully **without any API key**
- **Tests:** pytest (real PostgreSQL), Vitest + Testing Library
- **Deployment:** Docker Compose

## Quick start (Docker)

Needs Docker Desktop. From the project root:

```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
docker compose up --build
```

Then open **http://localhost:5173** and sign in as `analyst` / `analyst123` (see [Demo Credentials](#demo-credentials)).

The first start does the set-up for you (`python -m app.bootstrap` runs inside the backend container): it waits for
PostgreSQL, creates the schema with Alembic, and creates the three demo accounts. Starting again is safe and changes
nothing. If you already had a database from an earlier phase, it is detected and adopted without touching your data.

For a good demo, seed the baseline events once (this also lets the ML model train, which needs at least 5 time windows):

```bash
docker compose exec backend python scripts/seed_demo_data.py
```

| What | Where |
|---|---|
| App | http://localhost:5173 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |

Stop with `docker compose down`. Add `-v` only if you want to **delete the database** and start from scratch.

## Use a real AI model (optional)

The AI SOC analyst works offline out of the box. To have a real language model write the investigations, put a provider
and key in `.env` (for example `AI_PROVIDER=groq`, `AI_API_KEY=gsk_...`), recreate the backend
(`docker compose up -d --force-recreate backend`) and check it:

```bash
docker compose exec backend python scripts/check_ai.py
```

The **System Health** page then shows **live model**. A real model's reply is checked before use (its MITRE table is
replaced by the project's own mapping, and invented IP addresses or technique ids are removed), and any failure falls back
to the offline analyst, with the report saying so. Full steps, other providers and troubleshooting:
[docs/ai-analyst.md](docs/ai-analyst.md).

## Run without Docker

You still need PostgreSQL (`docker compose up -d postgres` is the easy way).

```bash
# backend (use a virtual environment; see docs/troubleshooting.md)
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://socuser:socpassword@localhost:5432/soc_db   # PowerShell: $env:DATABASE_URL="..."
python -m app.bootstrap
uvicorn app.main:app --reload

# frontend (second terminal)
cd frontend
npm ci
npm run dev
```

## The app

| Page | What it is |
|---|---|
| Dashboard | KPIs, live event feed, charts |
| Event Monitor | the raw event stream |
| Detection Engine | the five rules; enable/disable and tune thresholds live |
| ML Anomaly Detection | train the model on the event stream; top anomalous windows |
| Alerts | every rule match |
| Incidents | correlated alerts; open one for overview, timeline, evidence, entities, AI investigation, MITRE, response, audit |
| Risk Engine | how the score is built; incidents ranked by risk |
| AI SOC Analyst | pick an incident and investigate it |
| MITRE ATT&CK | technique coverage with real alert evidence |
| Threat Intelligence | states that no external feeds are queried (all data is synthetic) |
| Response Center | approve or reject recommended actions (simulated) |
| Audit Logs | who did what, when; append-only |
| Dataset & ML | upload, preprocess and train on public datasets with real metrics |
| Demo Mode | start the five attack scenarios |
| System Health | backend, ML model, AI analyst (live or offline) and simulator status |

## Documentation

| Doc | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | diagram, event pipeline, rules, risk score, data model, security model, known limitations |
| [docs/ai-analyst.md](docs/ai-analyst.md) | how investigations are produced, providers, the fallback |
| [docs/ml-and-datasets.md](docs/ml-and-datasets.md) | features, model, the no-labels-no-accuracy rule, NSL-KDD workflow |
| [docs/api-reference.md](docs/api-reference.md) | every endpoint and who may call it (generated from the code) |
| [docs/demo-script.md](docs/demo-script.md) | a 10-minute walkthrough and likely questions |
| [docs/troubleshooting.md](docs/troubleshooting.md) | fixes for the problems actually hit while building this |

## Roles

| Role | May do |
|---|---|
| VIEWER | read everything |
| SOC_ANALYST | read, plus change state: run scenarios, edit rules, train models, run investigations, approve/reject actions, upload datasets |
| ADMIN | the same as SOC_ANALYST |

A role is checked against the database on every request, not trusted from the token.

## Demo Credentials

**DEMO CREDENTIALS — NOT FOR PRODUCTION**

| Username | Password    | Role        |
|----------|-------------|-------------|
| admin    | admin123    | ADMIN       |
| analyst  | analyst123  | SOC_ANALYST |
| viewer   | viewer123   | VIEWER      |

Passwords are hashed with bcrypt before storage; the database never holds plaintext. Set `SEED_DEMO_USERS=false`
to stop the accounts being created.

## Project layout

```text
ai-cyber-defense/
├── backend/      FastAPI app (app/), Alembic migrations (alembic/), tests (tests/)
├── frontend/     React + TypeScript SPA (tests live beside the code)
├── scripts/      seed_demo_data, train_model, prepare_nslkdd, generate_api_docs, run_tests.sh
├── data/  ml/    uploaded datasets and trained models (contents are git-ignored)
├── docs/         documentation (see above)
├── docker-compose.yml
└── .env.example
```

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

## MITRE ATT&CK (Phase 11)

A dedicated `/mitre` page, built on the same `mitre_mapping.py` module
Phase 10 introduced for the AI analyst's output — one mapping, two
consumers, never two different answers to "what technique is this."

**System-wide coverage view:** shows all 5 of this project's rule-mapped
techniques (T1110 Brute Force, T1059.001 PowerShell, T1078 Valid
Accounts, T1071.004 DNS, T1041 Exfiltration Over C2), each with its real
observation history — alert count, incident count, last seen, and
clickable evidence linking straight to the incidents that triggered it.
A technique with zero alerts shows **no fabricated evidence** — just an
honest "not yet observed", dimmed in the table, rather than hiding the
row or inventing a count. Verified against the real `alerts` table:
every reported `alert_count` matched exactly, and every
`evidence_incident_id` resolved to a real incident.

**The Incident Page's MITRE tab** (`/incidents/:id`, placeholder since
Phase 9) is now real too: it shows this specific incident's own
mapping via a lightweight `GET /api/incidents/{id}/mitre` that doesn't
require running an AI investigation first. Cross-checked against the
AI analyst's independently-computed `mitre_mapping` field for the same
incident — they match exactly, since both read the same shared module.

**Read-only for every role, including VIEWER** — this is coverage
reporting, not a configurable control surface like Detection Rules.

One honest gap: every rule in the current demo database has fired at
least once, so the "zero alerts, not yet observed" display path
wasn't exercised by a live incident during testing — it's correct by
construction (the underlying SQL aggregates naturally return
`None`/empty for no matching rows, verified by reading the code path
directly), but it hasn't been seen live. A fresh database, or a rule
no scenario happens to trigger, will show it.

## Response Center (Phase 12)

The spec's 6 safe, simulated actions — Disable Account, Revoke
Session, Isolate Endpoint, Block Indicator, Reset Credentials, Create
Firewall Rule — with the full workflow: AI Recommendation → Analyst
Review → Approve/Reject → Mock Action → Result. **Nothing here ever
touches a real system.** Every result message says so explicitly.

**Recommendations are data-driven, not generic:** which actions get
suggested, and for what target, depends on the incident's own
`incident_type` and its real primary entity — an `account_compromise`
incident recommends Disable Account / Reset Credentials / Revoke
Session against the actual affected username; `endpoint_compromise`
recommends Isolate Endpoint against the actual affected hostname;
network/DNS incident types recommend Block Indicator / Create
Firewall Rule against the actual source IP. Generating recommendations
is idempotent — reopening the Response tab never duplicates them.

**Exact spec wording, verified, not assumed:** I generated a fresh
PowerShell-scenario incident specifically to exercise the one case the
spec gives a literal example for, and confirmed the real result message
character-for-character:
`Demo endpoint WIN-CLIENT-01 would be isolated. No real endpoint was modified.`
— with the real hostname substituted, not hardcoded.

**Two views, one data source:** the Incident Page's Response tab shows
one incident's own actions; the global `/response` Response Center
page is the cross-incident queue an analyst would actually triage
from, filterable by status (pending / approved / rejected). Both use
the same `ResponseActionCard` component and the same backend data —
verified the global queue's count exactly equals the sum of every
incident's own list.

**RBAC:** reading the queue (either view) works for every role,
including VIEWER; approving or rejecting requires ADMIN or
SOC_ANALYST — verified a VIEWER gets a clean `403`, and that an
already-decided action can't be decided again (`409`, not a silent
overwrite).

**API:** `GET /api/incidents/{id}/response` (incident-scoped, auto-
recommends on first open), `GET /api/response` (global queue, filter
by `?status_filter=`), `POST /api/response/{id}/approve`,
`POST /api/response/{id}/reject` — the last two match the spec's exact
endpoint paths.

A bug caught during testing, not shipped: my first pass serialized
`ResponseAction` via `ResponseActionOut.model_validate(action)`, which
crashed immediately because `action_label` is a computed field, not a
real column on the ORM model — Pydantic tries to read every schema
field straight off the object before any manual dict edits ever run.
Fixed with a proper `serialize_action()` helper shared by every
endpoint that returns a response action, so there's exactly one
correct serialization path, not several near-duplicates.

## Audit Logs (Phase 13)

The `audit_logs` table and a clean organizing principle for what gets
logged: **every `require_role`-gated route that changes state**, with
nothing missed and nothing fabricated. That's 6 call sites across 4
routers — simulator start/stop, detection rule updates, AI
investigations, and response action approve/reject — each calling one
shared `log_action()` helper.

`action`, `resource_type`, and `result` are free-text strings, not
enums, by design: unlike `Severity` (a genuine fixed 4-value domain),
the set of auditable actions will keep growing, and a new enum
migration for every new action type would be the wrong tool.

**Matches the spec's own example exactly:** approving a response
action logs `resource_type="incident"`, `resource_id=<the incident's
id>` — not the response action's own id — because that's what the
spec's literal example row shows (`"Approved simulated endpoint
isolation" | INC-1001 | SUCCESS`) and it's what lets the Incident
Page's Audit tab show everything relevant to one incident with a
single filtered query. Verified live: an approve action produced
exactly `Approved simulated block indicator | incident:INC-1071 |
SUCCESS`, and `GET /api/audit?resource_type=incident&resource_id=INC-1071`
returned both that entry and the investigation that preceded it.

**Real before/after values, not placeholders:** a detection rule
update's `old_value`/`new_value` captured the actual config change
(`query_threshold: 6 -> 7`), verified against what was actually sent.

**Two views:** the global `/audit` page (filterable by resource type,
expandable rows showing the full old/new value diff) and the Incident
Page's Audit tab — the **last placeholder tab**, now real — scoped to
just that incident, refreshing live when a response action gets
decided from the same page.

**Read-only for every role, including VIEWER** — accountability and
transparency, the same pattern as the MITRE coverage view.

**API:** `GET /api/audit` (matches the spec's exact endpoint path),
filterable by `resource_type`, `resource_id`, and `username`.

## Dataset & ML Training (Phase 14)

The `/dataset` page: upload a CSV or Parquet file, preprocess it, then
train and evaluate an Isolation Forest against it. Files can also be
dropped straight into `data/raw/` by hand — the file list is just a
directory listing, no hidden state.

**This is where the spec's conditional rule finally becomes real.**
Phase 6's `/ml` page trains on this project's own events, which have no
ground truth, so its accuracy is honestly "Not Applicable". Here, if
you name a **label column** (and which value(s) mean "attack"), the run
computes genuine accuracy, precision, recall, F1, and a full confusion
matrix with `sklearn.metrics` against it. Name no label column and it
reports "Not Applicable" again — never a made-up number either way.

**Workflow, with one deliberate consolidation:** Upload → Preprocess
(keeps numeric columns, drops rows with missing values, reports the
attack/normal distribution and which non-numeric columns were dropped)
→ Train & evaluate. The spec lists Train, Evaluate, and Save Model as
separate buttons; here they're one step, because there is nothing
meaningful for separate "Evaluate" and "Save" clicks to do beyond what
training already does (the same choice Phase 6 made).

**What was and wasn't verified — please read this part:**
- The evaluation pipeline was verified on two **synthetic toy datasets I
  generated** (200 rows -> 95% precision/recall; 100 rows -> a perfect
  1.0 because the classes have essentially zero overlap). In both, the
  confusion-matrix totals matched the true class counts exactly. **These
  numbers demonstrate that the metric code is correct. They say nothing
  about real-world detection quality** — a perfect score on a toy set
  with no class overlap is expected and not impressive. For genuine
  results, try a real labeled dataset such as NSL-KDD or CICIDS2017
  (numeric feature columns plus a label column).
- Both **CSV and Parquet** were exercised live. Parquet reads need
  `pyarrow`, now in `requirements.txt`.
- Upload, preprocess, and train were exercised through the Vite dev
  proxy (including the multipart upload), not just direct-to-backend.

**Four real bugs found and fixed during this phase:**
1. **`model_version` collisions.** Versions were stamped with
   second-level timestamps, so two training runs finishing in the same
   second hit the unique constraint. Now microsecond-precision. This
   was latent in Phase 6's `train.py` too, and is fixed there as well.
2. **API silently omitted the new fields.** I added `source` and
   `dataset_filename` to the ORM model but not to the `MLTrainingRunOut`
   response schema, so the API never returned them. Caught by a
   `KeyError` in verification; fixed in the schema and the TypeScript
   type.
3. **Path traversal on the read side.** Upload sanitized filenames, but
   preprocess/train built paths from the request body unchecked, so
   `../../elsewhere.csv` or an absolute path could read any CSV/Parquet
   on the server. Now every filename is resolved and must sit directly
   inside `data/raw/` or `data/processed/` (relative, absolute, and
   subdirectory-hidden traversal all verified blocked).
4. **Wrong data/model directory under Docker.** I located `data/` and
   `ml/models/` with `Path(__file__).parents[3]`, which is the repo root
   in a checkout but `/` inside the container (code lives at
   `/app/app/...`). Uploads and trained models would have landed in the
   container's own disposable filesystem instead of the `./data` and
   `./ml` folders mounted from the host, so hand-placing files in
   `data/raw/` wouldn't have worked in Docker. Phase 6's model directory
   had the same flaw. Both now use `app/utils/paths.py::project_root()`
   (a `PROJECT_ROOT` env var if set, otherwise the nearest ancestor
   containing `data/`), and `docker-compose.yml` now mounts `./ml:/app/ml`
   alongside `./data:/app/data`. Verified against a simulated Docker
   directory layout, the env override, and the normal checkout layout —
   **not** inside a real container, which I can't run here.

A migration note: the new `source` column is `NOT NULL`, so the
migration backfills existing rows with `event_stream` (which they
genuinely all were) via a temporary `server_default`, then drops it.

**API:** `GET /api/dataset/files`, `POST /api/dataset/upload`,
`POST /api/dataset/preprocess`, `POST /api/dataset/train` (the last
three ADMIN/SOC_ANALYST only, and all audit-logged like every other
privileged action), `GET /api/dataset/runs`.

### Training on real datasets from the command line (`scripts/train_model.py`)

The Dataset page is fine for small files, but NSL-KDD, UNSW-NB15 and
CICIDS2017 are big and awkward (CICIDS2017 is hundreds of MB per file),
so there is also a command. It uses the same preprocessing and training
code as the page, saves to the same table (runs appear in the page's
*Training history*), and is audit-logged as user `cli`.

**Where files go:** `data/raw/` in the project root, next to `backend/`
and `frontend/`. The folder is git-ignored, so the datasets are never
committed. Under Docker it is the same folder (mounted at `/app/data`).

**One-time setup (PowerShell, from the project root).** The command runs
on your machine, not in Docker, so point it at the database port Docker
publishes (Docker must be running):

```powershell
pip install -r backend\requirements.txt
$env:DATABASE_URL="postgresql+psycopg2://socuser:socpassword@localhost:5432/soc_db"
```

**NSL-KDD** (`KDDTrain+.txt` has no header row and dozens of attack
names, so a prep script labels it and keeps attacks to ~8%):

```powershell
python scripts\prepare_nslkdd.py "C:\path\to\KDDTrain+.txt" data\raw\nslkdd_binary.csv
python scripts\train_model.py nslkdd_binary.csv --label-column label --attack-values attack --contamination 0.08
```

**UNSW-NB15** (copy `UNSW_NB15_training-set.csv` into `data/raw/`; `label`
is 0/1 and `id` is just a row number):

```powershell
python scripts\train_model.py UNSW_NB15_training-set.csv --label-column label --attack-values 1 --drop-columns id --attack-fraction 0.08 --contamination 0.08
```

**CICIDS2017** (copy ONE day's CSV, one that contains attacks; Monday is
all benign. Tuesday has FTP/SSH brute force, roughly 3% of rows, so no
attack subsampling is needed):

```powershell
python scripts\train_model.py Tuesday-WorkingHours.pcap_ISCX.csv --label-column Label --benign-values BENIGN --max-rows 200000 --contamination 0.03
```

`--benign-values` means "everything except these is an attack", which is
what you want when a dataset has dozens of attack names. The tool strips
the leading spaces in CICIDS2017's column names, drops rows containing
`Infinity`/`NaN`, and tolerates the stray non-UTF-8 byte in its labels.

**Read results honestly:**
- Choosing `--contamination` to match the attack share you already know
  uses the labels to help the model, which flatters the scores. Say so.
- The model is evaluated on the same rows it was fitted on; there is no
  held-out test split.
- Isolation Forest is unsupervised; expect imperfect numbers on real data.

**What was verified:** the command was run end to end against synthetic
stand-ins reproducing each dataset's quirks (headerless NSL-KDD layout,
UNSW's `id` and text columns, CICIDS-style leading-space headers,
`Infinity`/`NaN` values, a stray invalid byte, many attack labels), and
every saved confusion matrix was cross-checked against an independent
recount of the data. **It has not been run on the real downloads.** If a
mirror's columns differ, the error messages print the actual column names.

Two further fixes made after the first Phase 14 delivery: the command
crashed at its final summary (it read a database object after closing
the session; found by running it), and a train request that named no label
column for a file preprocessed *with* one returned a raw HTTP 500; it is
now a clear 400.


## Testing (Phase 15)

One command runs everything: `./scripts/run_tests.sh` (backend, frontend, and a
production build). Current result: **567 backend tests, 94 frontend tests, build
green; 99% backend line coverage.**

### Backend (pytest) — `backend/tests/`

The suite runs against a **real PostgreSQL database**, not SQLite, because the
human-readable ids (`EVT-…`, `INC-1001`, …) come from Postgres sequences. Create
the throw-away test database once:

```bash
docker compose up -d postgres
docker compose exec postgres psql -U socuser -d soc_db -c "CREATE DATABASE soc_test;"
cd backend && pip install -r requirements.txt && pytest
```

Safety: the suite TRUNCATEs tables between tests, so `conftest.py` refuses to
run unless the database name ends in `_test`. Training and dataset tests write
to a temp directory, never to the real `data/` or `ml/models/`. Override the
target with `TEST_DATABASE_URL`.

| File | What it proves |
|---|---|
| `test_auth.py` | Login, JWT handling; forged / expired / `alg:none` / wrong-secret tokens rejected; a token's *claimed* role cannot escalate privileges (the DB role wins) |
| `test_rbac.py` | A matrix over every route: anonymous → 401, viewer → 403 on every write route, admin/analyst pass the role check |
| `test_detectors.py` | Each of the 5 rules: thresholds, windows, per-source isolation, debouncing, runtime configurability |
| `test_correlation.py` | Grouping scores, window limits, severity escalation, the explanation trail, "every alert in exactly one incident" |
| `test_risk_engine.py` | Five factors sum to ≤100, bounds hold for all inputs, deterministic, ML factor honest about missing models |
| `test_mitre_mapping.py` | Rule → technique mapping, coverage view, configured confidence |
| `test_response_center.py` | Recommendations, one-time decisions, and the **simulation-only guarantee** (approving "Disable Account" leaves the real user active) |
| `test_audit.py` | Every privileged action is logged; the log has no write/delete API |
| `test_ai_provider.py` | Mock provider output; **every** kind of LLM failure (HTTP errors, bad JSON, timeouts) falls back to a valid investigation; real-model robustness: tolerant parsing, the grounding guard, MITRE not taken from the model, rate-limit retry, the API key never leaking, the AI status endpoint |
| `test_check_ai.py` | The `scripts/check_ai.py` connection check: success, every kind of failure with a plain-language hint, and the key never printed |
| `test_ml.py` | Feature engineering, training honesty (no accuracy without labels), outlier ranked first, unique model versions |
| `test_dataset.py` | Upload allow-list, path traversal, preprocessing, real metrics only with labels |
| `test_simulator.py` | Scenario data uses only non-routable IPs / `.invalid` domains; the live runner streams over WebSocket |
| `test_bootstrap.py` | Fresh install builds the whole schema; migrations and models can't drift apart; existing databases are adopted without touching data; demo-account seeding; unreachable-database handling |
| `test_docs.py` | Every route is documented; every link in the README and docs resolves |
| `test_e2e_pipeline.py` | The full SOC loop incl. a quiet network raising **zero** alerts, and a complete analyst workflow over HTTP |

Scenario generators randomise users, hosts, IPs and byte volumes on every run,
so tests assert *rules and invariants*, never fixed values.

### Frontend (Vitest + Testing Library) — `frontend/src/**/*.test.tsx`

API client (auth header, error mapping, 401 handling, query strings, uploads),
auth context, route protection, login page, the Response Center and Audit Log
pages, the approve/reject card, and routing. `npm test` runs them;
`npm run build` type-checks the whole app including the tests.

### Bugs found and fixed while testing and documenting

* **Unvalidated training parameters (Phase 15).** `POST /api/ml/train` and `POST /api/dataset/train` accepted any
  `contamination` / `window_minutes`. Out-of-range values crashed with unhandled 500s (`window_minutes=0` raised
  `ZeroDivisionError`) and negative windows were silently recorded. Now a clean 422.
* **No migrations existed (Phase 16).** `alembic/versions/` was empty, so `alembic upgrade head` created nothing and a
  fresh `docker compose up` could not start. Added a baseline migration and a start-up bootstrap that also adopts existing databases.
* **A dataset run displaced the live ML model (Phase 16).** The ML page, dashboard chart and risk engine all used "the
  newest training run" of any kind, so training on an uploaded dataset (which has no per-IP predictions) blanked all three.
  They now use the newest *event-stream* run.
* **The ML factor never reached existing incidents (Phase 16).** Risk was scored once, when an incident formed, so a model
  trained afterwards never affected it. Training now re-scores existing incidents.
* **ML training was not audited (Phase 16).** Now recorded like every other privileged action.
* **Real-model path was fragile (Phase 17).** It sent a Groq model name to every provider, rejected any reply that wasn't
  perfectly shaped (code fences, a string instead of a list, `null`), trusted the model's MITRE table and anything it
  claimed, and gave no way to see why a call failed. It now has a per-provider model default, tolerant parsing, a grounding
  guard, a rate-limit retry, a diagnosable log (key masked), a status endpoint and a `check_ai.py` connection check.
* **Misleading UI text (Phase 16).** Sidebar pages said "Risk Engine ... lands in Phase 8" and the investigation tab said
  "isn't built yet" for features that were built. These are now real pages or accurate messages, and a test prevents regressions.

### Known limitations (documented, not hidden)

* `/ws/events` is intentionally unauthenticated (see `app/api/ws.py`).
* Denied (403) attempts are not written to the audit log — only successful
  privileged actions are.
* The real-LLM provider is tested against stub servers (including a real-HTTP one that misbehaves on purpose), not a live
  model in the build environment; run `scripts/check_ai.py` to verify your own key and model. The grounding guard checks
  IP addresses and technique ids, not usernames, hostnames or counts.

