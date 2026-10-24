"""Audit log (Phase 13): every privileged mutation is recorded; the log itself is append-only."""

import pytest

from app.models.audit_log import AuditLog
from app.services.audit import log_action

pytestmark = pytest.mark.security


def _entries(db, **filters):
    return db.query(AuditLog).filter_by(**filters).order_by(AuditLog.id).all()


def test_log_action_records_all_fields(db):
    log_action(db, username="analyst", action="Did a thing", resource_type="incident", resource_id="INC-1001",
               old_value={"a": 1}, new_value={"a": 2})
    (e,) = _entries(db)
    assert (e.username, e.action, e.resource_type, e.resource_id) == ("analyst", "Did a thing", "incident", "INC-1001")
    assert e.old_value == {"a": 1} and e.new_value == {"a": 2}
    assert e.result == "SUCCESS" and e.timestamp is not None


def test_rule_edit_is_audited_with_old_and_new_values(client, headers, db):
    r = client.post("/api/rules", headers=headers["analyst"],
                    json={"rule_key": "brute_force", "enabled": False, "config": {"failed_threshold": 9}})
    assert r.status_code == 200
    (e,) = _entries(db, resource_type="detection_rule")
    assert e.resource_id == "brute_force" and e.username == "analyst"
    assert e.old_value["enabled"] is True and e.old_value["config"]["failed_threshold"] == 5
    assert e.new_value["enabled"] is False and e.new_value["config"]["failed_threshold"] == 9
    assert e.new_value["config"]["window_minutes"] == 5            # merged, not replaced


def test_unknown_rule_key_is_404_and_not_audited(client, headers, db):
    assert client.post("/api/rules", headers=headers["admin"], json={"rule_key": "nope"}).status_code == 404
    assert _entries(db) == []


def test_simulator_start_and_stop_are_audited(client, headers, db):
    client.post("/api/simulator/start", headers=headers["analyst"], json={"scenario": "dns_anomaly"})
    client.post("/api/simulator/stop", headers=headers["analyst"])
    actions = [e.action for e in _entries(db, resource_type="simulator")]
    assert "Started demo scenario 'dns_anomaly'" in actions
    assert "Stopped demo scenario" in actions


def test_ml_training_via_dataset_is_audited(client, headers, db, ml_sandbox):
    client.post("/api/dataset/upload", headers=headers["admin"], files={"file": ("d.csv", b"a,b\n1,2\n3,4\n")})
    client.post("/api/dataset/preprocess", headers=headers["admin"], json={"raw_filename": "d.csv"})
    actions = [e.action for e in _entries(db, resource_type="dataset")]
    assert actions == ["Uploaded dataset 'd.csv'", "Preprocessed dataset 'd.csv'"]


# ----------------------------------------------------------------- reading
@pytest.fixture()
def populated(db):
    for user, rtype, rid in [("admin", "detection_rule", "brute_force"), ("analyst", "incident", "INC-1001"),
                             ("analyst", "incident", "INC-1002"), ("admin", "dataset", "x.csv")]:
        log_action(db, username=user, action=f"{user} on {rid}", resource_type=rtype, resource_id=rid)


def test_audit_log_is_readable_by_every_role_newest_first(client, headers, populated):
    for role in ("admin", "analyst", "viewer"):
        rows = client.get("/api/audit", headers=headers[role]).json()
        assert len(rows) == 4
        stamps = [r["timestamp"] for r in rows]
        assert stamps == sorted(stamps, reverse=True)


def test_audit_filters(client, headers, populated):
    h = headers["viewer"]
    assert len(client.get("/api/audit?username=analyst", headers=h).json()) == 2
    assert len(client.get("/api/audit?resource_type=incident", headers=h).json()) == 2
    assert [r["resource_id"] for r in client.get("/api/audit?resource_id=INC-1002", headers=h).json()] == ["INC-1002"]
    assert client.get("/api/audit?username=analyst&resource_type=dataset", headers=h).json() == []


@pytest.mark.parametrize("limit,status", [(0, 422), (501, 422), (1, 200), (500, 200)])
def test_audit_limit_is_bounded(client, headers, populated, limit, status):
    assert client.get(f"/api/audit?limit={limit}", headers=headers["viewer"]).status_code == status


def test_audit_filter_value_is_not_injectable(client, headers, populated):
    r = client.get("/api/audit", params={"username": "analyst' OR '1'='1"}, headers=headers["viewer"])
    assert r.status_code == 200 and r.json() == []


# -------------------------------------------------------------- append-only
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_the_audit_log_has_no_write_or_delete_api(client, headers, populated, method):
    """Even an ADMIN cannot edit or erase history through the API."""
    r = client.request(method, "/api/audit", headers=headers["admin"], json={})
    assert r.status_code == 405
    r = client.request(method, "/api/audit/1", headers=headers["admin"], json={})
    assert r.status_code in (404, 405)


def test_nothing_in_the_api_removes_audit_rows(client, headers, populated, db):
    before = db.query(AuditLog).count()
    for role in ("admin", "analyst"):
        client.post("/api/simulator/stop", headers=headers[role])
    assert db.query(AuditLog).count() >= before          # only ever grows
