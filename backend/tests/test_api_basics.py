"""Remaining read APIs: dashboard, events, alerts, detections, rules, assets, ids."""

import pytest

from helpers import replay_scenario
from app.utils.ids import next_alert_id, next_event_id, next_incident_id, next_response_id, parse_severity
from fastapi import HTTPException


# --------------------------------------------------------------------- health
def test_health_and_root(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["service"] == "AI Cyber Defense Command Center"
    assert client.get("/").json()["docs"] == "/docs"


# ------------------------------------------------------------------ dashboard
def test_dashboard_on_an_empty_system_is_honest(client, headers):
    d = client.get("/api/dashboard", headers=headers["viewer"]).json()
    assert d["data_status"] == "no_data"
    assert d["kpis"]["active_incidents"] == 0 and d["kpis"]["events_processed"] == 0
    assert d["kpis"]["detection_rate_pct"] is None          # never a fabricated metric
    assert d["live_events"] == [] and d["recent_incidents"] == []


def test_dashboard_reflects_a_real_attack(client, headers, db):
    alerts, (incident,) = replay_scenario(db, "multi_stage")
    d = client.get("/api/dashboard", headers=headers["viewer"]).json()
    assert d["data_status"] == "live"
    assert d["kpis"]["active_incidents"] == 1
    assert d["kpis"]["events_processed"] == 10
    assert d["kpis"]["critical_alerts"] == sum(1 for a in alerts if a.severity.value == "critical")
    assert d["kpis"]["systems_at_risk"] == 1
    assert [i["incident_id"] for i in d["recent_incidents"]] == [incident.incident_id]
    assert {c["category"] for c in d["charts"]["detection_type_distribution"]} >= {"Brute Force", "Abnormal Network Activity"}
    assert len(d["live_events"]) == 10


# ---------------------------------------------------------------- events/alerts
def test_events_list_filters_and_limit(client, headers, db):
    replay_scenario(db, "multi_stage")
    h = headers["viewer"]
    assert len(client.get("/api/events", headers=h).json()) == 10
    assert len(client.get("/api/events?limit=3", headers=h).json()) == 3
    auth = client.get("/api/events?source=authentication", headers=h).json()
    assert auth and all(e["source"] == "authentication" for e in auth)
    assert client.get("/api/events?severity=nonsense", headers=h).status_code == 400
    assert client.get("/api/events?limit=0", headers=h).status_code == 422
    stamps = [e["timestamp"] for e in client.get("/api/events", headers=h).json()]
    assert stamps == sorted(stamps, reverse=True)


def test_event_ids_have_the_documented_format(client, headers, db):
    replay_scenario(db, "powershell")
    assert all(e["event_id"].startswith("EVT-") and len(e["event_id"]) == 10
               for e in client.get("/api/events", headers=headers["viewer"]).json())


def test_alerts_and_detections_endpoints(client, headers, db):
    replay_scenario(db, "multi_stage")
    h = headers["viewer"]
    alerts = client.get("/api/alerts", headers=h).json()
    assert {a["rule_key"] for a in alerts} == {"brute_force", "impossible_travel", "suspicious_powershell", "abnormal_network"}
    assert [a["rule_key"] for a in client.get("/api/alerts?rule_key=brute_force", headers=h).json()] == ["brute_force"]
    assert all(a["severity"] == "critical" for a in client.get("/api/alerts?severity=critical", headers=h).json())
    assert client.get("/api/alerts?severity=bad", headers=h).status_code == 400
    assert len(client.get("/api/detections", headers=h).json()) == len(alerts)       # detections == alerts


# ---------------------------------------------------------------- rules / assets
def test_rules_list_and_runtime_update_changes_detection_behaviour(client, headers, db):
    h = headers["analyst"]
    rules = {r["rule_key"]: r for r in client.get("/api/rules", headers=h).json()}
    assert set(rules) == {"brute_force", "suspicious_powershell", "impossible_travel", "dns_anomaly", "abnormal_network"}

    # Turn the rule off through the API ...
    r = client.post("/api/rules", headers=h, json={"rule_key": "brute_force", "enabled": False})
    assert r.status_code == 200 and r.json()["enabled"] is False
    alerts, _ = replay_scenario(db, "brute_force")
    assert "brute_force" not in {a.rule_key for a in alerts}          # ... and it really stops firing, no restart

    # ... then raise a threshold and check config is merged, not replaced.
    r = client.post("/api/rules", headers=h, json={"rule_key": "dns_anomaly", "config": {"query_threshold": 99}})
    cfg = r.json()["config"]
    assert cfg["query_threshold"] == 99 and cfg["window_seconds"] == 60 and cfg["confidence"] == "medium"


def test_assets_are_listed_with_criticality(client, headers):
    assets = {a["hostname"]: a["criticality"] for a in client.get("/api/assets", headers=headers["viewer"]).json()}
    assert assets["WIN-SRV-DB01"] == "critical" and assets["WIN-CLIENT-01"] == "medium"


# -------------------------------------------------------------------- id helpers
def test_id_helpers_are_sequential_and_formatted(db):
    assert next_event_id(db) == (1, "EVT-000001") and next_event_id(db) == (2, "EVT-000002")
    assert next_alert_id(db) == (1, "ALT-000001")
    assert next_incident_id(db) == (1, "INC-1001")          # spec example: first incident is INC-1001
    assert next_response_id(db) == (1, "RESP-000001")


def test_parse_severity():
    assert parse_severity("HIGH").value == "high"
    with pytest.raises(HTTPException) as exc:
        parse_severity("extreme")
    assert exc.value.status_code == 400
