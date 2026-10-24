"""
Alert correlation (Phase 7): many alerts -> one incident.

Scoring recap (app/services/correlation.py): username +3, source IP +3,
hostname +2, destination IP +2, last alert <= 5 min +1, new kill-chain stage
+1; needs one strong entity match and a total >= 3.
"""

from datetime import timedelta

import pytest

from app.detectors.common import make_alert
from app.models.alert import Alert
from app.models.common import Severity
from app.models.incident import Incident, IncidentEvent
from app.services.correlation import (
    CORRELATION_WINDOW_MINUTES,
    backfill_uncorrelated_alerts,
    classify_incident,
    correlate_alert,
    correlate_alerts,
)
from helpers import make_event, now


def _alert(db, *, rule_key="brute_force", username="demo_user", ip="203.0.113.25", host="WIN-CLIENT-01",
           severity=Severity.HIGH, at=None, event_ids=None) -> Alert:
    alert = make_alert(
        db, rule_key=rule_key, rule_name=rule_key, title=f"{rule_key} test", severity=severity,
        detected_at=at or now(), triggering_event_ids=event_ids or [], username=username,
        source_ip=ip, hostname=host,
    )
    db.commit()
    db.refresh(alert)
    return alert


# --------------------------------------------------------------- grouping
def test_first_alert_opens_a_new_incident(db):
    a = _alert(db)
    incident, created = correlate_alert(db, a)
    db.commit()
    assert created is True
    assert incident.incident_id == "INC-1001"
    assert incident.alert_count == 1
    assert incident.status == "open"
    assert incident.severity == Severity.HIGH
    assert a.incident_id == incident.id
    assert incident.incident_metadata["correlation"][0]["reasons"] == ["first alert — opened a new incident"]


def test_same_user_and_ip_within_minutes_merge(db):
    t = now()
    a1 = _alert(db, rule_key="brute_force", at=t)
    a2 = _alert(db, rule_key="impossible_travel", at=t + timedelta(minutes=1))
    (i1, c1), = correlate_alerts(db, [a1])
    (i2, c2), = correlate_alerts(db, [a2])
    assert i1.id == i2.id and c1 is True and c2 is False
    assert i2.alert_count == 2
    assert db.query(Incident).count() == 1


def test_unrelated_entities_stay_separate(db):
    t = now()
    a1 = _alert(db, username="alice", ip="203.0.113.10", host="WIN-CLIENT-01", at=t)
    a2 = _alert(db, username="bob", ip="203.0.113.20", host="WIN-SRV-DB01", at=t + timedelta(seconds=30))
    correlate_alerts(db, [a1])
    correlate_alerts(db, [a2])
    assert db.query(Incident).count() == 2
    assert a1.incident_id != a2.incident_id


def test_hostname_alone_needs_proximity_to_merge(db):
    """Shared busy server, different people: only merge if close in time."""
    t = now()
    a1 = _alert(db, username="alice", ip="203.0.113.10", host="WIN-SRV-WEB01", at=t)
    near = _alert(db, rule_key="brute_force", username="bob", ip="203.0.113.20", host="WIN-SRV-WEB01",
                  at=t + timedelta(minutes=2))                       # 2 + 1 = 3 -> merges
    far = _alert(db, rule_key="brute_force", username="carol", ip="203.0.113.30", host="WIN-SRV-WEB01",
                 at=t + timedelta(minutes=9))                        # 2 + 0 = 2 -> does not
    correlate_alerts(db, [a1])
    correlate_alerts(db, [near])
    correlate_alerts(db, [far])
    assert near.incident_id == a1.incident_id
    assert far.incident_id != a1.incident_id


def test_alert_outside_the_window_opens_a_new_incident(db):
    t = now()
    a1 = _alert(db, at=t)
    a2 = _alert(db, at=t + timedelta(minutes=CORRELATION_WINDOW_MINUTES + 5))
    correlate_alerts(db, [a1])
    correlate_alerts(db, [a2])
    assert db.query(Incident).count() == 2


def test_closed_incidents_are_not_merge_candidates(db):
    t = now()
    a1 = _alert(db, at=t)
    (inc, _), = correlate_alerts(db, [a1])
    inc.status = "closed"
    db.commit()
    a2 = _alert(db, at=t + timedelta(minutes=1))
    correlate_alerts(db, [a2])
    assert a2.incident_id != inc.id
    assert db.query(Incident).count() == 2


def test_shared_destination_ip_adds_weight_but_is_not_enough_alone(db):
    t = now()
    e1 = make_event(db, source="network", event_type="network_anomaly", destination_ip="198.51.100.23", ts=t)
    e2 = make_event(db, source="network", event_type="network_anomaly", destination_ip="198.51.100.23", ts=t)
    a1 = _alert(db, rule_key="abnormal_network", username=None, ip="10.0.0.1", host="HOST-A", at=t, event_ids=[e1.id])
    a2 = _alert(db, rule_key="abnormal_network", username=None, ip="10.0.0.2", host="HOST-B", at=t, event_ids=[e2.id])
    correlate_alerts(db, [a1])
    correlate_alerts(db, [a2])
    assert a1.incident_id != a2.incident_id      # destination match alone is "weak"


# ------------------------------------------------------------ incident state
def test_severity_only_ever_escalates(db):
    t = now()
    a1 = _alert(db, severity=Severity.MEDIUM, at=t)
    a2 = _alert(db, rule_key="impossible_travel", severity=Severity.CRITICAL, at=t + timedelta(minutes=1))
    a3 = _alert(db, rule_key="suspicious_powershell", severity=Severity.LOW, at=t + timedelta(minutes=2))
    for a in (a1, a2, a3):
        correlate_alerts(db, [a])
    incident = db.query(Incident).one()
    assert incident.severity == Severity.CRITICAL
    assert incident.alert_count == 3


def test_time_bounds_follow_the_alerts(db):
    t = now()
    a1 = _alert(db, at=t)
    a2 = _alert(db, rule_key="impossible_travel", at=t + timedelta(minutes=3))
    correlate_alerts(db, [a1])
    correlate_alerts(db, [a2])
    incident = db.query(Incident).one()
    assert incident.first_seen == t
    assert incident.last_seen == t + timedelta(minutes=3)


def test_correlation_trail_explains_why(db):
    t = now()
    a1 = _alert(db, rule_key="brute_force", at=t)
    a2 = _alert(db, rule_key="suspicious_powershell", at=t + timedelta(minutes=1))
    correlate_alerts(db, [a1])
    correlate_alerts(db, [a2])
    trail = db.query(Incident).one().incident_metadata["correlation"]
    assert [step["alert_id"] for step in trail] == [a1.alert_id, a2.alert_id]
    reasons = " | ".join(trail[1]["reasons"])
    assert "same username (demo_user)" in reasons
    assert "same source IP (203.0.113.25)" in reasons
    assert "attack-chain progression" in reasons        # authentication -> endpoint
    assert trail[1]["score"] >= 3


def test_incident_entities_and_rules_accumulate(db):
    t = now()
    correlate_alerts(db, [_alert(db, rule_key="brute_force", at=t)])
    correlate_alerts(db, [_alert(db, rule_key="impossible_travel", at=t + timedelta(minutes=1))])
    meta = db.query(Incident).one().incident_metadata
    assert meta["rule_keys"] == ["brute_force", "impossible_travel"]
    assert meta["entities"]["usernames"] == ["demo_user"]
    assert meta["entities"]["source_ips"] == ["203.0.113.25"]


def test_linked_events_are_the_union_without_duplicates(db):
    t = now()
    events = [make_event(db, source="authentication", event_type="login", ts=t) for _ in range(3)]
    a1 = _alert(db, at=t, event_ids=[events[0].id, events[1].id])
    a2 = _alert(db, rule_key="impossible_travel", at=t + timedelta(minutes=1), event_ids=[events[1].id, events[2].id])
    correlate_alerts(db, [a1])
    correlate_alerts(db, [a2])
    linked = [row.event_id for row in db.query(IncidentEvent).all()]
    assert sorted(linked) == sorted(e.id for e in events)


def test_title_and_type_are_derived_from_the_rules_involved(db):
    t = now()
    correlate_alerts(db, [_alert(db, rule_key="brute_force", at=t)])
    incident = db.query(Incident).one()
    assert incident.incident_type == "account_compromise"
    assert incident.title == "Possible Account Compromise (demo_user)"


def test_invariant_every_alert_belongs_to_exactly_one_incident(db):
    t = now()
    batch = [
        _alert(db, username="alice", ip="203.0.113.1", host="H1", at=t),
        _alert(db, rule_key="impossible_travel", username="alice", ip="203.0.113.1", host="H1", at=t + timedelta(minutes=1)),
        _alert(db, username="bob", ip="203.0.113.2", host="H2", at=t + timedelta(minutes=2)),
        _alert(db, rule_key="dns_anomaly", username=None, ip="10.9.9.9", host="H3", at=t + timedelta(minutes=3)),
    ]
    correlate_alerts(db, batch)
    for incident in db.query(Incident).all():
        attached = db.query(Alert).filter(Alert.incident_id == incident.id).count()
        assert incident.alert_count == attached
    assert db.query(Alert).filter(Alert.incident_id.is_(None)).count() == 0


# ------------------------------------------------------------ classification
@pytest.mark.parametrize(
    "rules,expected",
    [
        ({"brute_force"}, "account_compromise"),
        ({"impossible_travel"}, "account_compromise"),
        ({"suspicious_powershell"}, "endpoint_compromise"),
        ({"dns_anomaly", "abnormal_network"}, "suspicious_network"),
        ({"dns_anomaly"}, "dns_anomaly"),
        ({"abnormal_network"}, "network_anomaly"),
        ({"brute_force", "suspicious_powershell", "abnormal_network"}, "account_compromise"),  # account wins
    ],
)
def test_classify_incident(rules, expected):
    assert classify_incident(rules)[0] == expected


# ------------------------------------------------------------------ backfill
def test_backfill_correlates_orphans_and_is_idempotent(db):
    t = now()
    orphans = [_alert(db, at=t), _alert(db, rule_key="impossible_travel", at=t + timedelta(minutes=1))]
    assert all(a.incident_id is None for a in orphans)
    assert backfill_uncorrelated_alerts(db) == 2
    db.expire_all()
    assert all(a.incident_id is not None for a in db.query(Alert).all())
    assert db.query(Incident).count() == 1
    assert backfill_uncorrelated_alerts(db) == 0
