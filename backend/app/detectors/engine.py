"""
Detection engine orchestrator.

`run_detectors` is called once per newly-inserted Event (from the
event simulator, right after it's committed). It re-reads the current
rule configs from the DB every time — not a cached copy — so an edit
made via `POST /api/rules` takes effect on the very next event with
no restart required.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.detectors import (
    abnormal_network,
    brute_force,
    dns_anomaly,
    impossible_travel,
    suspicious_powershell,
)
from app.detectors.defaults import DEFAULT_RULES
from app.models.alert import Alert
from app.models.detection_rule import DetectionRule
from app.models.event import Event
CHECKERS = {
    "brute_force": brute_force.check,
    "suspicious_powershell": suspicious_powershell.check,
    "impossible_travel": impossible_travel.check,
    "dns_anomaly": dns_anomaly.check,
    "abnormal_network": abnormal_network.check,
}
def ensure_default_rules(db: Session) -> None:
    existing_keys = set(db.scalars(select(DetectionRule.rule_key)))
    for rule_def in DEFAULT_RULES:
        if rule_def["rule_key"] in existing_keys:
            continue
        db.add(DetectionRule(**rule_def))
    db.commit()
def run_detectors(db: Session, event: Event) -> list[Alert]:
    rules = list(db.scalars(select(DetectionRule).where(DetectionRule.enabled.is_(True))))
    new_alerts: list[Alert] = []
    for rule in rules:
        checker = CHECKERS.get(rule.rule_key)
        if checker is None:
            continue
        alert = checker(db, event, rule)
        if alert is not None:
            new_alerts.append(alert)
    if new_alerts:
        db.commit()
        for alert in new_alerts:
            db.refresh(alert)

    return new_alerts
