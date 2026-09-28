"""
Alert correlation: many alerts -> one incident.

Correlation factors (from the project spec): same user, same IP, same
host, same destination, temporal proximity, related event type. Each
new alert is scored against every open incident that was active within
CORRELATION_WINDOW_MINUTES:

    shared username        +3   (strong)
    shared source IP       +3   (strong)
    shared hostname        +2   (strong)
    shared destination IP  +2
    last alert <= 5 min    +1   (temporal proximity)
    new kill-chain stage   +1   (related event type: authentication ->
                                 endpoint -> network progression)

An alert joins the best-scoring incident that has at least one strong
entity match and a total score >= MIN_CORRELATION_SCORE; otherwise it
opens a new incident. So a hostname match alone is not enough — it
needs proximity or chain progression too, which avoids merging
unrelated activity that merely shares a busy server.

Invariant: every alert belongs to exactly one incident. The reasons
behind each attachment are stored on the incident, so "why were these
grouped?" always has a concrete, inspectable answer.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.common import Severity
from app.models.event import Event
from app.models.incident import Incident, IncidentEvent
from app.utils.ids import next_incident_id

CORRELATION_WINDOW_MINUTES = 15
TEMPORAL_PROXIMITY_MINUTES = 5
MIN_CORRELATION_SCORE = 3

ENTITY_WEIGHTS = {
    "usernames": 3,
    "source_ips": 3,
    "hostnames": 2,
    "destination_ips": 2,
}
ENTITY_LABELS = {
    "usernames": "username",
    "source_ips": "source IP",
    "hostnames": "hostname",
    "destination_ips": "destination IP",
}
STRONG_ENTITY_TYPES = {"usernames", "source_ips", "hostnames"}

STAGE_BY_RULE = {
    "brute_force": "authentication",
    "impossible_travel": "authentication",
    "suspicious_powershell": "endpoint",
    "abnormal_network": "network",
    "dns_anomaly": "network",
}

SEVERITY_RANK = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}


def classify_incident(rule_keys: set[str]) -> tuple[str, str]:
    """(incident_type, human label) from the set of rules involved."""
    if rule_keys & {"brute_force", "impossible_travel"}:
        return "account_compromise", "Possible Account Compromise"
    if "suspicious_powershell" in rule_keys:
        return "endpoint_compromise", "Suspicious Endpoint Activity"
    if {"dns_anomaly", "abnormal_network"} <= rule_keys:
        return "suspicious_network", "Suspicious Network Activity"
    if "dns_anomaly" in rule_keys:
        return "dns_anomaly", "Anomalous DNS Activity"
    return "network_anomaly", "Abnormal Network Activity"


def _alert_entities(db: Session, alert: Alert) -> dict[str, set[str]]:
    destinations: set[str] = set()
    if alert.triggering_event_ids:
        destinations = set(
            db.scalars(
                select(Event.destination_ip).where(
                    Event.id.in_(alert.triggering_event_ids),
                    Event.destination_ip.is_not(None),
                )
            )
        )
    return {
        "usernames": {alert.username} if alert.username else set(),
        "source_ips": {alert.source_ip} if alert.source_ip else set(),
        "hostnames": {alert.hostname} if alert.hostname else set(),
        "destination_ips": destinations,
    }


def _incident_entities(incident: Incident) -> dict[str, set[str]]:
    stored = (incident.incident_metadata or {}).get("entities", {})
    return {key: set(stored.get(key, [])) for key in ENTITY_WEIGHTS}


def _score_candidate(
    alert: Alert, alert_entities: dict[str, set[str]], incident: Incident
) -> tuple[int, list[str]] | None:
    incident_entities = _incident_entities(incident)
    score = 0
    strong_matches = 0
    reasons: list[str] = []

    for entity_type, weight in ENTITY_WEIGHTS.items():
        shared = alert_entities[entity_type] & incident_entities[entity_type]
        if shared:
            score += weight
            if entity_type in STRONG_ENTITY_TYPES:
                strong_matches += 1
            reasons.append(
                f"same {ENTITY_LABELS[entity_type]} ({', '.join(sorted(shared))})"
            )

    if strong_matches == 0:
        return None

    gap_minutes = abs((alert.detected_at - incident.last_seen).total_seconds()) / 60
    if gap_minutes <= TEMPORAL_PROXIMITY_MINUTES:
        score += 1
        reasons.append(f"{gap_minutes:.1f} min from the incident's last alert")
    else:
        reasons.append(
            f"inside the {CORRELATION_WINDOW_MINUTES}-min window ({gap_minutes:.1f} min gap)"
        )

    incident_rules = set((incident.incident_metadata or {}).get("rule_keys", []))
    alert_stage = STAGE_BY_RULE.get(alert.rule_key)
    incident_stages = {STAGE_BY_RULE.get(k) for k in incident_rules} - {None}
    if alert_stage and incident_stages and alert_stage not in incident_stages:
        score += 1
        reasons.append(
            f"attack-chain progression ({'/'.join(sorted(incident_stages))} -> {alert_stage})"
        )

    if score < MIN_CORRELATION_SCORE:
        return None
    return score, reasons


def _apply_alert(
    db: Session,
    incident: Incident,
    alert: Alert,
    entities: dict[str, set[str]],
    score: int,
    reasons: list[str],
) -> None:
    meta = dict(incident.incident_metadata or {})
    merged = {key: set(v) for key, v in (meta.get("entities") or {}).items()}
    for key in ENTITY_WEIGHTS:
        merged.setdefault(key, set())
        merged[key] |= entities[key]

    rule_keys = set(meta.get("rule_keys", [])) | {alert.rule_key}
    trail = list(meta.get("correlation", []))
    trail.append(
        {
            "alert_id": alert.alert_id,
            "rule_key": alert.rule_key,
            "score": score,
            "reasons": reasons,
        }
    )
    incident.incident_metadata = {
        "entities": {key: sorted(v) for key, v in merged.items()},
        "rule_keys": sorted(rule_keys),
        "correlation": trail,
    }

    alert.incident_id = incident.id
    incident.alert_count = (incident.alert_count or 0) + 1
    incident.first_seen = min(incident.first_seen, alert.detected_at)
    incident.last_seen = max(incident.last_seen, alert.detected_at)
    if SEVERITY_RANK[alert.severity] > SEVERITY_RANK[incident.severity]:
        incident.severity = alert.severity

    incident.primary_username = incident.primary_username or alert.username
    incident.primary_source_ip = incident.primary_source_ip or alert.source_ip
    incident.primary_hostname = incident.primary_hostname or alert.hostname

    incident_type, label = classify_incident(rule_keys)
    subject = (
        incident.primary_username or incident.primary_hostname or incident.primary_source_ip
    )
    incident.incident_type = incident_type
    incident.title = f"{label} ({subject})" if subject else label

    already_linked = set(
        db.scalars(
            select(IncidentEvent.event_id).where(IncidentEvent.incident_id == incident.id)
        )
    )
    for event_id in alert.triggering_event_ids or []:
        if event_id not in already_linked:
            db.add(IncidentEvent(incident_id=incident.id, event_id=event_id))
            already_linked.add(event_id)


def correlate_alert(db: Session, alert: Alert) -> tuple[Incident, bool]:
    """Attach `alert` to the best matching open incident, or open a new
    one. Returns (incident, created). Caller commits."""
    entities = _alert_entities(db, alert)
    since = alert.detected_at - timedelta(minutes=CORRELATION_WINDOW_MINUTES)
    candidates = list(
        db.scalars(
            select(Incident).where(Incident.status == "open", Incident.last_seen >= since)
        )
    )

    best: tuple[int, list[str], Incident] | None = None
    for incident in candidates:
        scored = _score_candidate(alert, entities, incident)
        if scored is None:
            continue
        score, reasons = scored
        if best is None or score > best[0]:
            best = (score, reasons, incident)

    if best is not None:
        score, reasons, incident = best
        _apply_alert(db, incident, alert, entities, score, reasons)
        return incident, False

    incident_pk, incident_label = next_incident_id(db)
    incident = Incident(
        id=incident_pk,
        incident_id=incident_label,
        title="",
        incident_type="",
        severity=alert.severity,
        status="open",
        primary_username=alert.username,
        primary_source_ip=alert.source_ip,
        primary_hostname=alert.hostname,
        first_seen=alert.detected_at,
        last_seen=alert.detected_at,
        alert_count=0,
        incident_metadata={},
    )
    db.add(incident)
    db.flush()
    _apply_alert(
        db, incident, alert, entities, 0, ["first alert — opened a new incident"]
    )
    return incident, True


def correlate_alerts(db: Session, alerts: list[Alert]) -> list[tuple[Incident, bool]]:
    """Correlate a batch of freshly created alerts (in order) and commit.
    Returns each touched incident once, flagged created=True if it was
    opened during this batch."""
    touched: dict[int, list] = {}
    for alert in alerts:
        incident, created = correlate_alert(db, alert)
        if incident.id in touched:
            touched[incident.id][1] = touched[incident.id][1] or created
        else:
            touched[incident.id] = [incident, created]
        db.flush()
    db.commit()
    results = []
    for incident, created in touched.values():
        db.refresh(incident)
        results.append((incident, created))
    return results


def backfill_uncorrelated_alerts(db: Session) -> int:
    """Correlate any alert that has no incident yet (e.g. alerts created
    before Phase 7 existed), oldest first. Idempotent; run at startup."""
    pending = list(
        db.scalars(
            select(Alert).where(Alert.incident_id.is_(None)).order_by(Alert.detected_at)
        )
    )
    if not pending:
        return 0
    correlate_alerts(db, pending)
    return len(pending)
