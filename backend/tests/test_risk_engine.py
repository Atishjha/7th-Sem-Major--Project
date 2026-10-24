"""
Risk Engine (Phase 8): a transparent 0-100 score from five real factors.
Severity <=30, Asset criticality <=20, Detection confidence <=15,
Correlated alerts <=20, ML anomaly <=15  (sum of maxima = 100).
"""

from datetime import timedelta

import pytest

from app.models.common import Severity
from app.models.detection_rule import DetectionRule
from app.models.incident import Incident
from app.models.ml_prediction import MLPrediction
from app.models.ml_training_run import MLTrainingRun
from app.services.risk_engine import (
    CONFIDENCE_POINTS, CRITICALITY_POINTS, MAX_ALERT_POINTS, MAX_ML_POINTS, SEVERITY_POINTS,
    compute_risk_score, ensure_default_assets, recompute_all_incidents, recompute_and_save,
)
from app.utils.ids import next_incident_id
from helpers import now


def _incident(db, *, severity=Severity.MEDIUM, host="WIN-CLIENT-01", ip="203.0.113.25", alert_count=1,
              rule_keys=("brute_force",)) -> Incident:
    pk, label = next_incident_id(db)
    t = now()
    inc = Incident(
        id=pk, incident_id=label, title="t", incident_type="account_compromise", severity=severity,
        status="open", primary_username="demo_user", primary_source_ip=ip, primary_hostname=host,
        first_seen=t, last_seen=t, alert_count=alert_count, incident_metadata={"rule_keys": list(rule_keys)},
    )
    db.add(inc)
    db.commit()
    return inc


def _factor(breakdown, name):
    return next(f for f in breakdown if f["factor"] == name)


def _ml_run(db, version="v1") -> MLTrainingRun:
    run = MLTrainingRun(
        model_version=version, training_dataset="test", num_samples=10, num_features=10,
        feature_names=[], contamination=0.05, file_path="x", trained_at=now(),
    )
    db.add(run)
    db.commit()
    return run


def _prediction(db, run, ip, score, anomalous=True):
    db.add(MLPrediction(training_run_id=run.id, source_ip=ip, window_start=now(), features={},
                        anomaly_score=score, is_anomalous=anomalous))
    db.commit()


# ------------------------------------------------------------------ structure
def test_five_factors_whose_maximums_sum_to_100(db):
    _, breakdown = compute_risk_score(db, _incident(db))
    assert [f["factor"] for f in breakdown] == [
        "severity", "asset_criticality", "detection_confidence", "correlated_alerts", "ml_anomaly"
    ]
    assert sum(f["max_points"] for f in breakdown) == 100


def test_total_is_the_sum_of_the_parts(db):
    total, breakdown = compute_risk_score(db, _incident(db, severity=Severity.HIGH, alert_count=3))
    assert total == sum(f["points"] for f in breakdown)


def test_score_is_deterministic(db):
    inc = _incident(db, severity=Severity.HIGH, alert_count=2)
    assert compute_risk_score(db, inc) == compute_risk_score(db, inc)


@pytest.mark.parametrize("severity", list(Severity))
@pytest.mark.parametrize("host", ["WIN-SRV-DB01", "WIN-CLIENT-01", "UNREGISTERED-HOST", None])
@pytest.mark.parametrize("alerts", [0, 1, 5, 50])
def test_score_always_within_0_and_100(db, severity, host, alerts):
    total, breakdown = compute_risk_score(db, _incident(db, severity=severity, host=host, alert_count=alerts))
    assert 0 <= total <= 100
    assert all(0 <= f["points"] <= f["max_points"] for f in breakdown)


# ------------------------------------------------------------------- severity
def test_higher_severity_scores_strictly_higher(db):
    scores = [compute_risk_score(db, _incident(db, severity=s))[0]
              for s in (Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL)]
    assert scores == sorted(scores) and len(set(scores)) == 4


def test_severity_points_match_the_table(db):
    for s, pts in SEVERITY_POINTS.items():
        _, b = compute_risk_score(db, _incident(db, severity=s))
        assert _factor(b, "severity")["points"] == pts


# ------------------------------------------------------------ asset criticality
def test_registered_asset_uses_its_criticality(db):
    _, b = compute_risk_score(db, _incident(db, host="WIN-SRV-DB01"))
    f = _factor(b, "asset_criticality")
    assert f["points"] == CRITICALITY_POINTS[Severity.CRITICAL]
    assert f["detail"] == "WIN-SRV-DB01: critical"


def test_unregistered_host_gets_the_documented_default_tier(db):
    _, b = compute_risk_score(db, _incident(db, host="MYSTERY-BOX"))
    f = _factor(b, "asset_criticality")
    assert f["points"] == CRITICALITY_POINTS[Severity.MEDIUM]
    assert "default — not a registered asset" in f["detail"]


def test_incident_with_no_host_does_not_crash(db):
    _, b = compute_risk_score(db, _incident(db, host=None))
    assert _factor(b, "asset_criticality")["points"] == CRITICALITY_POINTS[Severity.MEDIUM]


def test_critical_server_outranks_workstation_all_else_equal(db):
    db_srv = compute_risk_score(db, _incident(db, host="WIN-SRV-DB01"))[0]
    client = compute_risk_score(db, _incident(db, host="WIN-CLIENT-01"))[0]
    assert db_srv > client


# ----------------------------------------------------------- correlated alerts
@pytest.mark.parametrize("count,expected", [(0, 0), (1, 4), (3, 12), (5, 20), (6, 20), (40, 20)])
def test_alert_points_are_four_each_capped_at_twenty(db, count, expected):
    _, b = compute_risk_score(db, _incident(db, alert_count=count))
    assert _factor(b, "correlated_alerts")["points"] == expected <= MAX_ALERT_POINTS


# ------------------------------------------------------------------ confidence
def test_confidence_comes_from_the_rules_configuration(db):
    _, b = compute_risk_score(db, _incident(db, rule_keys=("brute_force",)))   # default: high
    assert _factor(b, "detection_confidence")["points"] == CONFIDENCE_POINTS["high"]

    rule = db.query(DetectionRule).filter_by(rule_key="brute_force").one()
    rule.config = {**rule.config, "confidence": "low"}
    db.commit()
    _, b = compute_risk_score(db, _incident(db, rule_keys=("brute_force",)))
    assert _factor(b, "detection_confidence")["points"] == CONFIDENCE_POINTS["low"]


def test_highest_confidence_among_the_incidents_rules_wins(db):
    _, b = compute_risk_score(db, _incident(db, rule_keys=("dns_anomaly", "brute_force")))  # medium + high
    f = _factor(b, "detection_confidence")
    assert f["points"] == CONFIDENCE_POINTS["high"]
    assert "brute_force" in f["detail"]


def test_no_rules_falls_back_to_medium(db):
    _, b = compute_risk_score(db, _incident(db, rule_keys=()))
    assert _factor(b, "detection_confidence")["points"] == CONFIDENCE_POINTS["medium"]


# ------------------------------------------------------------------- ML factor
def test_ml_factor_is_zero_and_says_why_when_no_model_exists(db):
    _, b = compute_risk_score(db, _incident(db))
    f = _factor(b, "ml_anomaly")
    assert f["points"] == 0
    assert f["detail"] == {"available": False, "reason": "no ML model trained yet"}


def test_ml_factor_scales_the_matching_anomaly_score(db):
    run = _ml_run(db)
    _prediction(db, run, "203.0.113.25", 0.8)
    _prediction(db, run, "203.0.113.25", 0.4)           # lower score for same IP is ignored
    _, b = compute_risk_score(db, _incident(db, ip="203.0.113.25"))
    f = _factor(b, "ml_anomaly")
    assert f["points"] == round(0.8 * MAX_ML_POINTS) == 12
    assert f["detail"]["matched"] is True and f["detail"]["source_ip"] == "203.0.113.25"


def test_ml_factor_ignores_non_anomalous_and_other_ips(db):
    run = _ml_run(db)
    _prediction(db, run, "203.0.113.25", 0.9, anomalous=False)
    _prediction(db, run, "10.0.0.99", 0.99)
    _, b = compute_risk_score(db, _incident(db, ip="203.0.113.25"))
    f = _factor(b, "ml_anomaly")
    assert f["points"] == 0 and f["detail"] == {"available": True, "matched": False}


def test_ml_factor_only_uses_the_latest_training_run(db):
    old = _ml_run(db, "old")
    _prediction(db, old, "203.0.113.25", 0.95)
    new = _ml_run(db, "new")
    new.trained_at = old.trained_at + timedelta(minutes=5)
    db.commit()
    _, b = compute_risk_score(db, _incident(db, ip="203.0.113.25"))
    assert _factor(b, "ml_anomaly")["points"] == 0


def test_ml_factor_with_no_source_ip(db):
    _ml_run(db)
    _, b = compute_risk_score(db, _incident(db, ip=None))
    assert _factor(b, "ml_anomaly")["detail"]["reason"] == "incident has no source IP to match"


# ------------------------------------------------------------------ persistence
def test_recompute_and_save_stores_score_and_breakdown_without_losing_metadata(db):
    inc = _incident(db, severity=Severity.HIGH)
    recompute_and_save(db, inc)
    db.commit()
    db.refresh(inc)
    assert inc.risk_score is not None and 0 <= inc.risk_score <= 100
    assert len(inc.incident_metadata["risk_breakdown"]) == 5
    assert "risk_computed_at" in inc.incident_metadata
    assert inc.incident_metadata["rule_keys"] == ["brute_force"]          # untouched


def test_recompute_all_is_idempotent_and_returns_the_count(db):
    for s in (Severity.LOW, Severity.HIGH):
        _incident(db, severity=s)
    assert recompute_all_incidents(db) == 2
    first = sorted(i.risk_score for i in db.query(Incident).all())
    assert recompute_all_incidents(db) == 2
    db.expire_all()
    assert sorted(i.risk_score for i in db.query(Incident).all()) == first


def test_default_assets_seed_is_idempotent(db):
    from app.models.asset import Asset

    ensure_default_assets(db)
    ensure_default_assets(db)
    assert db.query(Asset).count() == 4
