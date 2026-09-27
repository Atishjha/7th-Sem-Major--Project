"""
Rule 5 — Abnormal Network Activity.

Unusual number of destinations or outbound bytes, read from the
network-anomaly event's own metadata against configurable thresholds.
"""

from sqlalchemy.orm import Session

from app.detectors.common import make_alert
from app.models.common import Severity
from app.models.detection_rule import DetectionRule
from app.models.event import Event


def check(db: Session, event: Event, rule: DetectionRule):
    if event.source != "network" or event.event_type != "network_anomaly":
        return None

    dest_threshold = rule.config.get("unique_destination_threshold", 10)
    bytes_threshold = rule.config.get("bytes_sent_threshold", 50_000_000)
    bytes_critical_threshold = rule.config.get(
        "bytes_sent_critical_threshold", 200_000_000
    )

    unique_destinations = event.event_metadata.get("unique_destinations")
    bytes_sent = event.event_metadata.get("bytes_sent")

    triggered_by = []
    if unique_destinations is not None and unique_destinations >= dest_threshold:
        triggered_by.append("unique_destinations")
    if bytes_sent is not None and bytes_sent >= bytes_threshold:
        triggered_by.append("bytes_sent")

    if not triggered_by:
        return None

    if bytes_sent is not None and bytes_sent >= bytes_critical_threshold:
        severity = Severity.CRITICAL
    elif "bytes_sent" in triggered_by:
        severity = Severity.HIGH
    else:
        severity = Severity.MEDIUM

    return make_alert(
        db,
        rule_key="abnormal_network",
        rule_name=rule.name,
        title=f"Abnormal network activity on {event.hostname or event.source_ip}",
        severity=severity,
        detected_at=event.timestamp,
        triggering_event_ids=[event.id],
        username=event.username,
        source_ip=event.source_ip,
        hostname=event.hostname,
        metadata={
            "triggered_by": triggered_by,
            "unique_destinations": unique_destinations,
            "bytes_sent": bytes_sent,
        },
    )
