"""
Rule -> MITRE ATT&CK technique mapping.

Real, public ATT&CK data (technique ids/names/tactics are factual,
not invented). "Confidence" reuses each rule's own `confidence`
setting from Phase 8 (app/detectors/defaults.py) rather than a
separate fabricated number — one rule, one confidence, used
everywhere it's needed.

This module is intentionally small and shared: Phase 10 (AI
Investigation) uses it to populate the investigation's MITRE section;
Phase 11 builds the dedicated MITRE ATT&CK browsing page on top of the
same mapping.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.detection_rule import DetectionRule

RULE_TECHNIQUES: dict[str, list[dict]] = {
    "brute_force": [
        {"tactic": "Credential Access", "technique_id": "T1110", "technique_name": "Brute Force"},
    ],
    "suspicious_powershell": [
        {"tactic": "Execution", "technique_id": "T1059.001", "technique_name": "Command and Scripting Interpreter: PowerShell"},
    ],
    "impossible_travel": [
        {"tactic": "Initial Access", "technique_id": "T1078", "technique_name": "Valid Accounts"},
    ],
    "dns_anomaly": [
        {"tactic": "Command and Control", "technique_id": "T1071.004", "technique_name": "Application Layer Protocol: DNS"},
    ],
    "abnormal_network": [
        {"tactic": "Exfiltration", "technique_id": "T1041", "technique_name": "Exfiltration Over C2 Channel"},
    ],
}


def techniques_for_rules(db: Session, rule_keys: list[str]) -> list[dict]:
    rules = {
        r.rule_key: r
        for r in db.scalars(select(DetectionRule).where(DetectionRule.rule_key.in_(rule_keys)))
    }
    out = []
    for key in rule_keys:
        confidence = rules[key].config.get("confidence", "medium") if key in rules else "medium"
        for technique in RULE_TECHNIQUES.get(key, []):
            out.append({**technique, "confidence": confidence, "evidence_rule": key})
    return out


def aggregate_technique_observations(db: Session) -> list[dict]:
    """System-wide view, Phase 11: every technique this project's rules
    CAN map to, each marked with whether it has actually fired here and
    the real evidence if so. Rules never fired still appear — showing
    detection coverage honestly includes "configured but not yet
    observed", not just what happened to trigger.
    """
    rules = {r.rule_key: r for r in db.scalars(select(DetectionRule))}

    observations: list[dict] = []
    for rule_key, techniques in RULE_TECHNIQUES.items():
        rule = rules.get(rule_key)
        confidence = rule.config.get("confidence", "medium") if rule else "medium"

        stats = db.execute(
            select(
                func.count(Alert.id),
                func.count(func.distinct(Alert.incident_id)),
                func.min(Alert.detected_at),
                func.max(Alert.detected_at),
            ).where(Alert.rule_key == rule_key)
        ).one()
        alert_count, incident_count, first_seen, last_seen = stats

        evidence_alerts = list(
            db.scalars(
                select(Alert.alert_id)
                .where(Alert.rule_key == rule_key)
                .order_by(Alert.detected_at.desc())
                .limit(5)
            )
        )
        evidence_incidents = list(
            db.scalars(
                select(func.distinct(Alert.incident_id))
                .where(Alert.rule_key == rule_key, Alert.incident_id.is_not(None))
                .order_by(Alert.incident_id.desc())
                .limit(5)
            )
        )
        # resolve incident PKs -> human-readable incident_id strings
        evidence_incident_labels: list[str] = []
        if evidence_incidents:
            from app.models.incident import Incident

            evidence_incident_labels = list(
                db.scalars(
                    select(Incident.incident_id).where(Incident.id.in_(evidence_incidents))
                )
            )

        for technique in techniques:
            observations.append({
                **technique,
                "confidence": confidence,
                "evidence_rule": rule_key,
                "alert_count": alert_count or 0,
                "incident_count": incident_count or 0,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "evidence_alert_ids": evidence_alerts,
                "evidence_incident_ids": evidence_incident_labels,
            })

    observations.sort(key=lambda o: (-o["alert_count"], o["technique_id"]))
    return observations
