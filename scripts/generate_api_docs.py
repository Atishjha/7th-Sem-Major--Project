"""
Generate docs/api-reference.md from the running application.

Nothing here is hand-written: every route comes from the real FastAPI app,
and each route's access level is *measured* by calling it:

  * no token            -> 401  => requires sign-in, otherwise public
  * VIEWER token        -> 403  => needs ADMIN or SOC_ANALYST, otherwise any signed-in role

Run (needs the database from docker compose or a local Postgres):

    DATABASE_URL=postgresql+psycopg2://socuser:socpassword@localhost:5432/soc_db \
        python scripts/generate_api_docs.py

Probing is safe: write routes reject a viewer with 403 before doing anything,
and the only unauthenticated writes (login) are sent an empty body.
"""

import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _candidate in (ROOT / "backend", ROOT):
    if (_candidate / "app" / "__init__.py").exists():
        sys.path.insert(0, str(_candidate))
        break

from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.bootstrap import migrate, seed_demo_users  # noqa: E402
from app.database.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.security.jwt import create_access_token  # noqa: E402


# Hand-written, because docstrings are developer notes. Access levels are NOT
# written here; they are measured. A route missing from this table stops the
# script, so the reference cannot silently go stale.
DESCRIPTIONS = {
    ("GET", "/"): "Service banner with a pointer to the docs.",
    ("GET", "/api/health"): "Liveness check: service name, environment and server time.",
    ("POST", "/api/auth/login"): "Exchange username and password for a JWT (JSON body).",
    ("GET", "/api/auth/me"): "Profile of the signed-in user (never includes the password hash).",
    ("GET", "/api/dashboard"): "KPIs, charts, recent incidents and live-event feed for the dashboard.",
    ("GET", "/api/events"): "Raw events, newest first. Filters: `limit`, `source`, `severity`.",
    ("GET", "/api/alerts"): "Alerts raised by the detection rules. Filters: `limit`, `rule_key`, `severity`.",
    ("GET", "/api/detections"): "Same records as alerts, exposed under the name the spec uses.",
    ("GET", "/api/rules"): "The detection rules with their live configuration.",
    ("POST", "/api/rules"): "Enable/disable a rule or merge new settings into its config; takes effect immediately and is audited.",
    ("POST", "/api/simulator/start"): "Start a demo scenario (`brute_force`, `powershell`, `dns_anomaly`, `network_anomaly`, `multi_stage`). 409 if one is already running.",
    ("POST", "/api/simulator/stop"): "Stop the running scenario.",
    ("GET", "/api/simulator/status"): "Whether a scenario is running and how far along it is.",
    ("GET", "/api/ml/status"): "Whether an event-stream model is trained, plus its latest run (dataset runs are listed under `/api/dataset/runs`).",
    ("POST", "/api/ml/train"): "Train the Isolation Forest on the stored event stream (`contamination` 0-0.5, `window_minutes` 1-1440), then re-score existing incidents with it. Audited.",
    ("GET", "/api/ml/predictions"): "Anomaly scores from the latest run, highest first. Filters: `limit`, `anomalous_only`.",
    ("GET", "/api/incidents"): "Incidents with risk score and breakdown. Filters: `limit`, `status`, `severity`.",
    ("GET", "/api/incidents/{incident_id}"): "One incident with its alerts, evidence events and correlation trail.",
    ("POST", "/api/incidents/{incident_id}/investigate"): "Run the AI SOC analyst on the incident and store the structured report.",
    ("GET", "/api/incidents/{incident_id}/investigation"): "The latest stored investigation, or `null` if none has been run.",
    ("GET", "/api/incidents/{incident_id}/mitre"): "MITRE ATT&CK techniques that apply to this incident, with the rule that evidences each.",
    ("GET", "/api/incidents/{incident_id}/response"): "Recommended response actions for the incident; created on first request, never duplicated.",
    ("GET", "/api/assets"): "Registered assets and their criticality (used by the risk engine).",
    ("GET", "/api/mitre/techniques"): "Coverage view: every mapped technique and how much real alert evidence exists for it.",
    ("GET", "/api/response"): "The global response queue. Filter: `status_filter` (recommended, simulated_success, rejected).",
    ("POST", "/api/response/{response_id}/approve"): "Approve a recommended action. The outcome is simulated and explicitly says nothing real changed. Audited.",
    ("POST", "/api/response/{response_id}/reject"): "Reject a recommended action; no action is taken. Audited.",
    ("GET", "/api/audit"): "Append-only audit trail, newest first. Filters: `limit`, `username`, `resource_type`, `resource_id`.",
    ("GET", "/api/dataset/files"): "Raw (uploaded) and processed dataset files.",
    ("POST", "/api/dataset/upload"): "Upload a `.csv` or `.parquet` file (multipart). Other types are rejected.",
    ("POST", "/api/dataset/preprocess"): "Clean a raw file into a numeric feature table (optionally keeping a label column).",
    ("POST", "/api/dataset/train"): "Train on a processed file. Accuracy metrics are computed only if labels are declared.",
    ("GET", "/api/dataset/runs"): "Training runs that came from uploaded datasets.",
}

OUT = ROOT / "docs" / "api-reference.md"
TAG_TITLES = OrderedDict()


def sample_path(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "X", path)


def probe(client, method, path, headers):
    kwargs = {"headers": headers}
    if method in {"POST", "PUT", "PATCH"}:
        kwargs["json"] = {}
    return client.request(method, path, **kwargs).status_code


def main() -> None:
    migrate(engine)
    seed_demo_users()
    viewer = {"Authorization": "Bearer " + create_access_token(username="viewer", role="VIEWER")}

    rows = []
    with TestClient(app) as client:
        for route in app.routes:
            if not isinstance(route, APIRoute) or route.path.startswith(("/docs", "/openapi", "/redoc")):
                continue
            for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                path = sample_path(route.path)
                if probe(client, method, path, {}) != 401:
                    access = "public"
                elif probe(client, method, path, viewer) == 403:
                    access = "ADMIN, SOC_ANALYST"
                else:
                    access = "any signed-in role"
                tag = (route.tags or ["other"])[0]
                if (method, route.path) not in DESCRIPTIONS:
                    raise SystemExit(f"No description for {method} {route.path}: add it to DESCRIPTIONS.")
                rows.append((tag, method, route.path, access, DESCRIPTIONS[(method, route.path)]))

    groups = OrderedDict()
    for tag, method, path, access, desc in rows:
        groups.setdefault(tag, []).append((method, path, access, desc))

    lines = [
        "# API reference",
        "",
        "> **Generated** by `scripts/generate_api_docs.py` from the running application. Do not edit by hand;",
        "> re-run the script after changing a route. Interactive docs are also served at `/docs` (Swagger UI).",
        "",
        "All routes live under `/api` and need `Authorization: Bearer <token>` (get one from `POST /api/auth/login`)",
        "unless marked **public**. Roles: **ADMIN**, **SOC_ANALYST** (may change state) and **VIEWER** (read-only).",
        "Access levels below were measured by calling each route as an anonymous user and as a viewer.",
        "",
        f"**{len(rows)} HTTP routes + 1 WebSocket.**",
        "",
    ]
    for tag, items in groups.items():
        lines += [f"## {tag}", "", "| Method | Path | Access | Description |", "|---|---|---|---|"]
        for method, path, access, desc in items:
            lines.append(f"| `{method}` | `{path}` | {access} | {desc} |")
        lines.append("")
    lines += [
        "## WebSocket",
        "",
        "| Path | Access | Description |",
        "|---|---|---|",
        "| `/ws/events` | public (demo simplification) | Live stream of simulator `event`, `alert`, `incident` and `status` messages. |",
        "",
    ]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} routes in {len(groups)} groups")


if __name__ == "__main__":
    main()
