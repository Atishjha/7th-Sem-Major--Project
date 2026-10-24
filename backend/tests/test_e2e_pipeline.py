"""
End-to-end: the whole SOC loop, from raw telemetry to an audited response.

  events -> rule detection -> correlation -> risk score -> MITRE mapping
         -> ML anomaly scoring -> AI investigation -> analyst decision -> audit trail

Telemetry is replayed through the same detect/correlate/score steps the live
simulator runs (see helpers.replay_scenario); everything after that goes over
real HTTP with real logins, exactly as the React app would call it.
"""

from datetime import timedelta

import pytest

from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.incident import Incident
from app.models.user import User
from helpers import failed_login, ingest, make_event, now, replay_scenario, successful_login

pytestmark = pytest.mark.e2e


def _login(client, username, password):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _quiet_baseline(db, n_ips=25):
    """A normal working day on the network: a few successful logins, one typo, light DNS."""
    t = now() - timedelta(minutes=40)
    for i in range(n_ips):
        ip = f"192.168.56.{i + 20}"
        user = f"user{i}"
        ingest(db, successful_login(db, user=user, ip=ip, host=f"WIN-CLIENT-{i:02d}", ts=t + timedelta(minutes=i)))
        for j in range(2):                                              # a couple of DNS lookups, well under threshold
            ingest(db, make_event(db, source="dns", event_type="dns_query", source_ip=ip, ts=t + timedelta(minutes=i, seconds=10 * j),
                                  hostname=f"WIN-CLIENT-{i:02d}", metadata={"domain": "intranet.invalid"}))
    ingest(db, failed_login(db, ip="192.168.56.20", user="user0", ts=t + timedelta(minutes=30)))   # one honest typo


# ----------------------------------------------------------------- false positives
def test_a_quiet_network_raises_no_alerts_and_no_incidents(db):
    _quiet_baseline(db)
    assert db.query(Alert).count() == 0
    assert db.query(Incident).count() == 0


def test_baseline_noise_does_not_hide_a_real_attack(db):
    _quiet_baseline(db)
    alerts, incidents = replay_scenario(db, "multi_stage")
    assert {a.rule_key for a in alerts} == {"brute_force", "impossible_travel", "suspicious_powershell", "abnormal_network"}
    assert len(incidents) == 1 and db.query(Incident).count() == 1


# --------------------------------------------------------------- the attack itself
def test_multi_stage_attack_becomes_one_critical_scored_incident(db):
    alerts, (incident,) = replay_scenario(db, "multi_stage")
    db.refresh(incident)

    assert len(alerts) == 4 and incident.alert_count == 4
    assert incident.incident_type == "account_compromise"
    # exfiltration volume is randomised (50-500 MB; >=200 MB is critical), so the
    # incident is high OR critical -- what must hold is that it follows its worst alert
    assert incident.severity.value in {"high", "critical"}
    assert incident.severity == max((a.severity for a in alerts), key=lambda sev: ["low", "medium", "high", "critical"].index(sev.value))
    assert incident.incident_id == "INC-1001"
    assert set(incident.incident_metadata["rule_keys"]) == {
        "brute_force", "impossible_travel", "suspicious_powershell", "abnormal_network"}

    # risk: bounded, explained, and built from real factors
    assert 0 < incident.risk_score <= 100
    factors = {f["factor"]: f for f in incident.incident_metadata["risk_breakdown"]}
    from app.services.risk_engine import SEVERITY_POINTS
    assert factors["severity"]["points"] == SEVERITY_POINTS[incident.severity]
    assert factors["correlated_alerts"]["points"] == 16         # 4 alerts x 4
    assert factors["detection_confidence"]["points"] == 15      # brute_force is configured "high"

    # correlation explains itself: later alerts cite why they joined
    trail = incident.incident_metadata["correlation"]
    assert len(trail) == 4 and trail[0]["reasons"] == ["first alert — opened a new incident"]
    assert all(step["score"] >= 3 for step in trail[1:])


@pytest.mark.parametrize(
    "scenario,incident_type",
    [("brute_force", "account_compromise"), ("powershell", "endpoint_compromise"),
     ("dns_anomaly", "dns_anomaly"), ("network_anomaly", "network_anomaly")],
)
def test_each_single_stage_scenario_yields_the_expected_incident_type(db, scenario, incident_type):
    _alerts, incidents = replay_scenario(db, scenario)
    assert len(incidents) == 1
    assert incidents[0].incident_type == incident_type
    assert 0 < incidents[0].risk_score <= 100


def test_ml_flags_the_attacker_and_feeds_the_risk_score(db, ml_sandbox):
    from app.ml.train import train_and_score
    from app.services.risk_engine import recompute_and_save

    _quiet_baseline(db)
    _alerts, (incident,) = replay_scenario(db, "multi_stage")
    before = incident.risk_score
    ml_factor = next(f for f in incident.incident_metadata["risk_breakdown"] if f["factor"] == "ml_anomaly")
    assert ml_factor["points"] == 0 and ml_factor["detail"]["available"] is False

    run = train_and_score(db, contamination=0.1)
    assert run.accuracy_status == "not_applicable"

    recompute_and_save(db, incident)
    db.commit()
    db.refresh(incident)
    ml_factor = next(f for f in incident.incident_metadata["risk_breakdown"] if f["factor"] == "ml_anomaly")
    assert ml_factor["detail"]["available"] is True
    assert ml_factor["detail"]["matched"] is True, "the attacker's source IP should be among the flagged windows"
    assert ml_factor["points"] > 0
    assert incident.risk_score > before


# ----------------------------------------------------------- the analyst's workflow
def test_full_analyst_workflow_over_http(client, db, users, ml_sandbox):
    # 1. A multi-stage attack happens.
    _alerts, (seeded,) = replay_scenario(db, "multi_stage")

    # 2. The analyst signs in for real (bcrypt + JWT), no shortcuts.
    analyst = _login(client, "analyst", "analyst123")

    # 3. The dashboard shows it.
    dash = client.get("/api/dashboard", headers=analyst).json()
    assert dash["kpis"]["active_incidents"] == 1 and dash["data_status"] == "live"

    # 4. They open the incident: alerts, evidence events, risk, MITRE.
    inc_id = client.get("/api/incidents", headers=analyst).json()[0]["incident_id"]
    detail = client.get(f"/api/incidents/{inc_id}", headers=analyst).json()
    assert len(detail["alerts"]) == 4 and len(detail["events"]) >= 8
    assert {t["technique_id"] for t in client.get(f"/api/incidents/{inc_id}/mitre", headers=analyst).json()} == {
        "T1110", "T1078", "T1059.001", "T1041"}

    # 5. They ask the AI analyst (offline mock) for an investigation.
    report = client.post(f"/api/incidents/{inc_id}/investigate", headers=analyst).json()
    assert report["observed_evidence"] and report["generated_by"].startswith("mock")
    assert detail["primary_source_ip"] in " ".join(report["indicators"])

    # 6. The Response tab recommends actions targeting the real account.
    actions = client.get(f"/api/incidents/{inc_id}/response", headers=analyst).json()
    assert {a["action_type"] for a in actions} == {"disable_account", "reset_credentials", "revoke_session"}
    assert all(a["target"] == detail["primary_username"] for a in actions)

    # 7. They approve one and reject another.
    disable = next(a for a in actions if a["action_type"] == "disable_account")
    reset = next(a for a in actions if a["action_type"] == "reset_credentials")
    approved = client.post(f"/api/response/{disable['response_id']}/approve", headers=analyst).json()
    rejected = client.post(f"/api/response/{reset['response_id']}/reject", headers=analyst).json()
    assert approved["status"] == "simulated_success" and "No real account was modified" in approved["result_message"]
    assert rejected["status"] == "rejected"

    # 8. Re-opening the tab doesn't resurrect decided actions or duplicate anything.
    again = client.get(f"/api/incidents/{inc_id}/response", headers=analyst).json()
    assert len(again) == 3
    assert sorted(a["status"] for a in again) == ["recommended", "rejected", "simulated_success"]

    # 9. Everything privileged left a trail, attributed to the right person and incident.
    log = client.get(f"/api/audit?resource_id={inc_id}", headers=analyst).json()
    assert {e["action"] for e in log} == {
        "Ran AI investigation", "Approved simulated disable account", "Rejected simulated reset credentials"}
    assert all(e["username"] == "analyst" and e["result"] == "SUCCESS" for e in log)

    # 10. A viewer sees all of it, but can change none of it.
    viewer = _login(client, "viewer", "viewer123")
    assert client.get(f"/api/incidents/{inc_id}", headers=viewer).status_code == 200
    assert client.get("/api/audit", headers=viewer).status_code == 200
    assert client.post(f"/api/incidents/{inc_id}/investigate", headers=viewer).status_code == 403
    pending = next(a for a in again if a["status"] == "recommended")
    assert client.post(f"/api/response/{pending['response_id']}/approve", headers=viewer).status_code == 403

    # 11. And the simulated "disable account" never touched a real account.
    assert all(u.is_active for u in db.query(User).all())


def test_a_second_attack_gets_its_own_incident(db):
    _a1, (first,) = replay_scenario(db, "powershell")
    first_id = first.id
    first.status = "closed"                                    # analyst closed the first one
    db.commit()
    _a2, incidents = replay_scenario(db, "powershell")
    assert len(incidents) == 1 and incidents[0].id != first_id
    assert db.query(Incident).count() == 2
