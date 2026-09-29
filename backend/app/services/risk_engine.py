"""
Risk Engine: a transparent, capped 0-100 score per incident, computed
from real data — never a random number.

Five factors, weighted to sum to at most 100:

    Severity              max 30   incident's own (max-across-alerts) severity
    Asset Criticality     max 20   looked up from the assets table by hostname
    Detection Confidence  max 15   each rule's own configured confidence
    Correlated Alerts     max 20   4 points per alert, capped at 20 (5+ alerts)
    ML Anomaly            max 15   latest Isolation Forest score for a matching
                                    source IP/user, or 0 if no model/match yet

"Indicator Reputation" from the spec's example is intentionally left
out: there is no threat-intel module in this project yet, so rather
than fabricate a number for it, it simply isn't one of the factors —
the breakdown only ever shows factors backed by real data.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.asset import Asset
from app.models.common import Severity
from app.models.detection_rule import DetectionRule
from app.models.incident import Incident
from app.models.ml_prediction import MLPrediction
from app.models.ml_training_run import MLTrainingRun

DEFAULT_ASSETS = [
    {"hostname": "WIN-SRV-DB01", "criticality": Severity.CRITICAL, "description": "Primary database server"},
    {"hostname": "WIN-SRV-WEB01", "criticality": Severity.HIGH, "description": "Public-facing web server"},
    {"hostname": "WIN-CLIENT-01", "criticality": Severity.MEDIUM, "description": "Staff workstation"},
    {"hostname": "WIN-CLIENT-02", "criticality": Severity.MEDIUM, "description": "Staff workstation"},
]
# Hosts not in the table above (e.g. freshly-generated demo hostnames from
# the multi_stage scenario) get this tier — documented, not fabricated.
DEFAULT_CRITICALITY = Severity.MEDIUM

SEVERITY_POINTS = {Severity.LOW: 8, Severity.MEDIUM: 18, Severity.HIGH: 25, Severity.CRITICAL: 30}
CRITICALITY_POINTS = {Severity.LOW: 5, Severity.MEDIUM: 10, Severity.HIGH: 15, Severity.CRITICAL: 20}
CONFIDENCE_POINTS = {"low": 5, "medium": 10, "high": 15}
CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
POINTS_PER_ALERT = 4
MAX_ALERT_POINTS = 20
MAX_ML_POINTS = 15


def ensure_default_assets(db: Session) -> None:
    existing = set(db.scalars(select(Asset.hostname)))
    for a in DEFAULT_ASSETS:
        if a["hostname"] in existing:
            continue
        db.add(Asset(**a))
    db.commit()


def _asset_criticality(db: Session, hostname: str | None) -> tuple[Severity, bool]:
    """Returns (criticality, was_known_asset)."""
    if hostname:
        asset = db.scalar(select(Asset).where(Asset.hostname == hostname))
        if asset:
            return asset.criticality, True
    return DEFAULT_CRITICALITY, False


def _detection_confidence(db: Session, rule_keys: list[str]) -> tuple[str, str | None]:
    """Highest confidence among the incident's own rules, and which rule
    it came from (for the breakdown detail line)."""
    if not rule_keys:
        return "medium", None
    rules = list(db.scalars(select(DetectionRule).where(DetectionRule.rule_key.in_(rule_keys))))
    best_key, best_conf = None, "medium"
    for r in rules:
        conf = r.config.get("confidence", "medium")
        if best_key is None or CONFIDENCE_RANK.get(conf, 1) > CONFIDENCE_RANK.get(best_conf, 1):
            best_key, best_conf = r.rule_key, conf
    return best_conf, best_key


def _ml_anomaly_factor(db: Session, incident: Incident) -> tuple[int, dict]:
    latest_run_id = db.scalar(
        select(MLTrainingRun.id).order_by(MLTrainingRun.trained_at.desc()).limit(1)
    )
    if latest_run_id is None:
        return 0, {"available": False, "reason": "no ML model trained yet"}

    candidate_ips = {incident.primary_source_ip} if incident.primary_source_ip else set()
    if not candidate_ips:
        return 0, {"available": False, "reason": "incident has no source IP to match"}

    best = db.scalar(
        select(MLPrediction)
        .where(
            MLPrediction.training_run_id == latest_run_id,
            MLPrediction.source_ip.in_(candidate_ips),
            MLPrediction.is_anomalous.is_(True),
        )
        .order_by(MLPrediction.anomaly_score.desc())
        .limit(1)
    )
    if best is None:
        return 0, {"available": True, "matched": False}

    points = round(best.anomaly_score * MAX_ML_POINTS)
    return points, {
        "available": True,
        "matched": True,
        "source_ip": best.source_ip,
        "anomaly_score": round(best.anomaly_score, 3),
    }


def compute_risk_score(db: Session, incident: Incident) -> tuple[int, list[dict]]:
    breakdown: list[dict] = []

    sev_points = SEVERITY_POINTS[incident.severity]
    breakdown.append({
        "factor": "severity", "label": "Severity", "points": sev_points,
        "max_points": max(SEVERITY_POINTS.values()),
        "detail": incident.severity.value,
    })

    criticality, known = _asset_criticality(db, incident.primary_hostname)
    crit_points = CRITICALITY_POINTS[criticality]
    breakdown.append({
        "factor": "asset_criticality", "label": "Asset Criticality", "points": crit_points,
        "max_points": max(CRITICALITY_POINTS.values()),
        "detail": (
            f"{incident.primary_hostname}: {criticality.value}"
            if known else f"{incident.primary_hostname or 'unknown host'}: "
                          f"{criticality.value} (default — not a registered asset)"
        ),
    })

    rule_keys = (incident.incident_metadata or {}).get("rule_keys", [])
    confidence, from_rule = _detection_confidence(db, rule_keys)
    conf_points = CONFIDENCE_POINTS[confidence]
    breakdown.append({
        "factor": "detection_confidence", "label": "Detection Confidence", "points": conf_points,
        "max_points": max(CONFIDENCE_POINTS.values()),
        "detail": f"{confidence} (from {from_rule})" if from_rule else confidence,
    })

    alert_points = min(MAX_ALERT_POINTS, incident.alert_count * POINTS_PER_ALERT)
    breakdown.append({
        "factor": "correlated_alerts", "label": "Correlated Alerts", "points": alert_points,
        "max_points": MAX_ALERT_POINTS,
        "detail": f"{incident.alert_count} alert(s) x {POINTS_PER_ALERT}, capped at {MAX_ALERT_POINTS}",
    })

    ml_points, ml_detail = _ml_anomaly_factor(db, incident)
    breakdown.append({
        "factor": "ml_anomaly", "label": "ML Anomaly", "points": ml_points,
        "max_points": MAX_ML_POINTS, "detail": ml_detail,
    })

    total = sum(f["points"] for f in breakdown)
    return total, breakdown


def recompute_and_save(db: Session, incident: Incident) -> Incident:
    total, breakdown = compute_risk_score(db, incident)
    incident.risk_score = total
    meta = dict(incident.incident_metadata or {})
    meta["risk_breakdown"] = breakdown
    meta["risk_computed_at"] = datetime.now(timezone.utc).isoformat()
    incident.incident_metadata = meta
    db.add(incident)
    return incident


def recompute_all_incidents(db: Session) -> int:
    """Backfill/refresh every incident's risk score. Pure function of
    current state, so always safe to re-run (e.g. at every startup)."""
    incidents = list(db.scalars(select(Incident)))
    for incident in incidents:
        recompute_and_save(db, incident)
    db.commit()
    return len(incidents)
