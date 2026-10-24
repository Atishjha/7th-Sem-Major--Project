"""
Response Center (Phase 12): recommend -> analyst approves/rejects -> SIMULATED result.

The most important property here is the safety one: nothing an analyst approves
may touch a real account, host, session, credential or firewall.
"""

import re

import pytest

from app.models.audit_log import AuditLog
from app.models.common import Severity
from app.models.incident import Incident
from app.models.response_action import ActionStatus, ActionType, ResponseAction
from app.models.user import User
from app.services.response_center import (
    ACTION_LABELS, RECOMMENDATION_RULES, _result_message, approve_action, create_recommended_actions,
    reject_action, serialize_action,
)
from app.utils.ids import next_incident_id
from helpers import now, replay_scenario


def _incident(db, incident_type, *, username="demo_user", ip="203.0.113.25", host="WIN-CLIENT-01") -> Incident:
    pk, label = next_incident_id(db)
    t = now()
    inc = Incident(
        id=pk, incident_id=label, title="t", incident_type=incident_type, severity=Severity.HIGH, status="open",
        primary_username=username, primary_source_ip=ip, primary_hostname=host,
        first_seen=t, last_seen=t, alert_count=1, incident_metadata={},
    )
    db.add(inc)
    db.commit()
    return inc


# ---------------------------------------------------------- recommendations
@pytest.mark.parametrize(
    "incident_type,expected",
    [
        ("account_compromise", {(ActionType.DISABLE_ACCOUNT, "demo_user"), (ActionType.RESET_CREDENTIALS, "demo_user"),
                                (ActionType.REVOKE_SESSION, "demo_user")}),
        ("endpoint_compromise", {(ActionType.ISOLATE_ENDPOINT, "WIN-CLIENT-01")}),
        ("suspicious_network", {(ActionType.BLOCK_INDICATOR, "203.0.113.25"), (ActionType.CREATE_FIREWALL_RULE, "203.0.113.25")}),
        ("dns_anomaly", {(ActionType.BLOCK_INDICATOR, "203.0.113.25")}),
        ("network_anomaly", {(ActionType.BLOCK_INDICATOR, "203.0.113.25")}),
    ],
)
def test_recommendations_target_the_incidents_real_entities(db, incident_type, expected):
    actions = create_recommended_actions(db, _incident(db, incident_type))
    assert {(a.action_type, a.target) for a in actions} == expected
    assert all(a.status == ActionStatus.RECOMMENDED and a.response_id.startswith("RESP-") for a in actions)
    assert all(a.recommended_reason for a in actions)


def test_every_known_incident_type_has_recommendations():
    from app.services.correlation import classify_incident

    reachable = {classify_incident(k)[0] for k in (
        {"brute_force"}, {"suspicious_powershell"}, {"dns_anomaly", "abnormal_network"}, {"dns_anomaly"}, {"abnormal_network"})}
    assert reachable <= set(RECOMMENDATION_RULES)


def test_recommending_twice_never_duplicates(db):
    inc = _incident(db, "account_compromise")
    assert len(create_recommended_actions(db, inc)) == 3
    assert create_recommended_actions(db, inc) == []
    assert db.query(ResponseAction).count() == 3


def test_missing_target_entity_means_no_placeholder_action(db):
    """No username on the incident -> don't invent a 'disable account ???' action."""
    assert create_recommended_actions(db, _incident(db, "account_compromise", username=None)) == []


def test_unknown_incident_type_gets_nothing(db):
    assert create_recommended_actions(db, _incident(db, "something_new")) == []


# ------------------------------------------------- the simulation-only guarantee
@pytest.mark.parametrize("action_type", list(ActionType))
def test_every_action_type_has_a_label_and_a_result_that_says_nothing_real_changed(action_type):
    assert action_type in ACTION_LABELS
    message = _result_message(action_type, "TARGET")
    assert "TARGET" in message
    assert "would be" in message                       # conditional, not "was"
    assert re.search(r"No real .+ (was|were) modified\.$", message.rstrip())


def test_approving_disable_account_does_not_disable_the_real_account(client, headers, db, users):
    """The recommended target 'demo_user' is made a REAL user here; approving
    'Disable Account' must leave that row exactly as it was."""
    victim = User(username="demo_user", hashed_password="x", is_active=True)
    db.add(victim)
    db.commit()
    inc = _incident(db, "account_compromise")
    create_recommended_actions(db, inc)
    disable = db.query(ResponseAction).filter_by(action_type=ActionType.DISABLE_ACCOUNT).one()

    r = client.post(f"/api/response/{disable.response_id}/approve", headers=headers["analyst"])
    assert r.status_code == 200
    db.expire_all()
    assert db.query(User).filter_by(username="demo_user").one().is_active is True


# ------------------------------------------------------------------- decisions
@pytest.fixture()
def action(db, users):
    inc = _incident(db, "endpoint_compromise")
    (a,) = create_recommended_actions(db, inc)
    return a


def test_approve_marks_simulated_success_with_a_clear_message(client, headers, action):
    r = client.post(f"/api/response/{action.response_id}/approve", headers=headers["analyst"])
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "simulated_success"
    assert body["decided_by_username"] == "analyst" and body["decided_at"]
    assert body["result_message"] == "Demo endpoint WIN-CLIENT-01 would be isolated. No real endpoint was modified."
    assert body["action_label"] == "Isolate Endpoint"


def test_reject_records_the_decision_and_takes_no_action(client, headers, action):
    r = client.post(f"/api/response/{action.response_id}/reject", headers=headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "rejected"
    assert body["result_message"] == "Rejected by analyst; no action taken."
    assert body["decided_by_username"] == "admin"


@pytest.mark.parametrize("first,second", [("approve", "approve"), ("approve", "reject"), ("reject", "approve"), ("reject", "reject")])
def test_an_action_can_only_be_decided_once(client, headers, action, first, second):
    assert client.post(f"/api/response/{action.response_id}/{first}", headers=headers["analyst"]).status_code == 200
    r = client.post(f"/api/response/{action.response_id}/{second}", headers=headers["analyst"])
    assert r.status_code == 409
    assert "already" in r.json()["detail"]


def test_unknown_response_id_is_404(client, headers, users):
    for verb in ("approve", "reject"):
        assert client.post(f"/api/response/RESP-999999/{verb}", headers=headers["analyst"]).status_code == 404


def test_viewer_cannot_decide_and_the_action_stays_recommended(client, headers, action, db):
    assert client.post(f"/api/response/{action.response_id}/approve", headers=headers["viewer"]).status_code == 403
    db.expire_all()
    assert db.get(ResponseAction, action.id).status == ActionStatus.RECOMMENDED


def test_decisions_are_audited_against_the_incident(client, headers, action, db):
    client.post(f"/api/response/{action.response_id}/approve", headers=headers["analyst"])
    entry = db.query(AuditLog).one()
    inc = db.get(Incident, action.incident_id)
    assert entry.action == "Approved simulated isolate endpoint"
    assert entry.resource_type == "incident" and entry.resource_id == inc.incident_id
    assert entry.old_value == {"status": "recommended"}
    assert entry.new_value["status"] == "simulated_success"
    assert entry.username == "analyst"


def test_service_level_decisions_stamp_who_and_when(db, users, action):
    approve_action(db, action, users["admin"])
    assert action.decided_by_username == "admin" and action.decided_at is not None


def test_serialize_action_includes_label(db, action):
    assert serialize_action(action).action_label == "Isolate Endpoint"


# --------------------------------------------------------------------- queue
def test_global_queue_and_status_filter(client, headers, db, users):
    alerts, (incident,) = replay_scenario(db, "brute_force")
    client.get(f"/api/incidents/{incident.incident_id}/response", headers=headers["viewer"])   # creates 3 actions
    queue = client.get("/api/response", headers=headers["viewer"]).json()
    assert len(queue) == 3
    first = queue[0]["response_id"]
    client.post(f"/api/response/{first}/reject", headers=headers["analyst"])

    assert len(client.get("/api/response?status_filter=recommended", headers=headers["viewer"]).json()) == 2
    assert len(client.get("/api/response?status_filter=rejected", headers=headers["viewer"]).json()) == 1
    assert client.get("/api/response?status_filter=bogus", headers=headers["viewer"]).status_code == 400
