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
- [x] Phase 3 — Dashboard (this phase)
- [x] Phase 3 — Dashboard
- [x] Phase 4 — Event simulator
- [x] Phase 5 — Rule detection
- [ ] Phase 6 — ML anomaly detection
- [ ] Phase 7 — Alert correlation
- [ ] Phase 8 — Risk engine
- [ ] Phase 9 — Incident page
- [ ] Phase 10 — AI SOC Analyst
- [ ] Phase 11 — MITRE ATT&CK
- [ ] Phase 12 — Response Center
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
