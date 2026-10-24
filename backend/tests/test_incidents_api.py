"""Incident endpoints (Phases 9-12) driven through HTTP after replaying real scenarios."""

import pytest

from app.models.audit_log import AuditLog
from helpers import replay_scenario


@pytest.fixture()
def attack(db, client, headers):
    """A completed brute-force + impossible-travel attack, ready to query."""
    alerts, incidents = replay_scenario(db, "brute_force")
    return incidents[0]


def test_list_incidents(client, headers, attack):
    r = client.get("/api/incidents", headers=headers["viewer"])
    assert r.status_code == 200
    (row,) = r.json()
    assert row["incident_id"] == attack.incident_id
    assert row["incident_type"] == "account_compromise"
    assert row["alert_count"] == 2
    assert 0 <= row["risk_score"] <= 100


def test_list_incidents_filters(client, headers, attack):
    ok = client.get("/api/incidents?status=open&severity=high", headers=headers["viewer"]).json()
    assert len(ok) == 1
    assert client.get("/api/incidents?status=closed", headers=headers["viewer"]).json() == []
    assert client.get("/api/incidents?severity=critical", headers=headers["viewer"]).json() == []


def test_invalid_severity_filter_is_a_400_not_a_500(client, headers, attack):
    r = client.get("/api/incidents?severity=catastrophic", headers=headers["viewer"])
    assert r.status_code == 400
    assert "Expected one of" in r.json()["detail"]


@pytest.mark.parametrize("limit,status", [(0, 422), (201, 422), (-1, 422), (1, 200), (200, 200)])
def test_list_limit_is_bounded(client, headers, attack, limit, status):
    assert client.get(f"/api/incidents?limit={limit}", headers=headers["viewer"]).status_code == status


def test_incident_detail_includes_ordered_alerts_and_events(client, headers, attack):
    r = client.get(f"/api/incidents/{attack.incident_id}", headers=headers["viewer"])
    assert r.status_code == 200
    body = r.json()
    assert [a["rule_key"] for a in body["alerts"]] == ["brute_force", "impossible_travel"]
    assert len(body["events"]) >= 6
    stamps = [e["timestamp"] for e in body["events"]]
    assert stamps == sorted(stamps)
    assert {"risk_breakdown", "correlation", "entities", "rule_keys"} <= set(body["incident_metadata"])


def test_unknown_incident_is_404_everywhere(client, headers):
    for path in ("", "/mitre", "/investigation", "/response"):
        r = client.get(f"/api/incidents/INC-9999{path}", headers=headers["viewer"])
        assert r.status_code == 404, path
    assert client.post("/api/incidents/INC-9999/investigate", headers=headers["analyst"]).status_code == 404


def test_incident_mitre_endpoint(client, headers, attack):
    r = client.get(f"/api/incidents/{attack.incident_id}/mitre", headers=headers["viewer"])
    assert {t["technique_id"] for t in r.json()} == {"T1110", "T1078"}


# --------------------------------------------------------- AI investigation
def test_investigation_is_none_until_one_is_run(client, headers, attack):
    r = client.get(f"/api/incidents/{attack.incident_id}/investigation", headers=headers["viewer"])
    assert r.status_code == 200 and r.json() is None


def test_run_investigation_returns_the_full_structure_and_is_persisted(client, headers, attack):
    r = client.post(f"/api/incidents/{attack.incident_id}/investigate", headers=headers["analyst"])
    assert r.status_code == 200
    body = r.json()
    for field in (
        "executive_summary", "what_happened", "timeline_summary", "observed_evidence", "inference",
        "affected_assets", "indicators", "mitre_mapping", "risk_explanation",
        "recommended_investigation", "recommended_containment", "recommended_remediation",
        "unknown_information", "questions_for_analyst", "generated_by", "generated_at",
    ):
        assert field in body, field
    assert body["observed_evidence"] and body["inference"]
    assert body["observed_evidence"] != body["inference"]          # facts and interpretation stay separate

    again = client.get(f"/api/incidents/{attack.incident_id}/investigation", headers=headers["viewer"]).json()
    assert again["executive_summary"] == body["executive_summary"]


def test_investigation_is_audited(client, headers, attack, db):
    client.post(f"/api/incidents/{attack.incident_id}/investigate", headers=headers["analyst"])
    entry = db.query(AuditLog).filter(AuditLog.action == "Ran AI investigation").one()
    assert entry.username == "analyst"
    assert entry.resource_type == "incident" and entry.resource_id == attack.incident_id
    assert entry.result == "SUCCESS"


# ------------------------------------------------------------ response actions
def test_opening_the_response_tab_recommends_actions_idempotently(client, headers, attack):
    first = client.get(f"/api/incidents/{attack.incident_id}/response", headers=headers["viewer"]).json()
    second = client.get(f"/api/incidents/{attack.incident_id}/response", headers=headers["viewer"]).json()
    assert {a["action_type"] for a in first} == {"disable_account", "reset_credentials", "revoke_session"}
    assert all(a["status"] == "recommended" and a["target"] == attack.primary_username for a in first)
    assert [a["response_id"] for a in first] == [a["response_id"] for a in second]
