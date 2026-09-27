"""
Rule 4 — DNS Anomaly.

Unusually high DNS request frequency from the same source within a
short window. Computed from raw dns_query events (not from the
scenario generator's own summary event), so the rule genuinely
detects the pattern rather than trusting a pre-labeled signal.
"""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.detectors.common import has_recent_open_alert, make_alert
from app.models.common import Severity
from app.models.detection_rule import DetectionRule
from app.models.event import Event


def check(db: Session, event: Event, rule: DetectionRule):
    if event.source != "dns" or event.event_type != "dns_query":
        return None
    if not event.source_ip:
        return None

    threshold = rule.config.get("query_threshold", 6)
    window_seconds = rule.config.get("window_seconds", 60)
    since = event.timestamp - timedelta(seconds=window_seconds)

    stmt = select(func.count()).where(
        Event.source == "dns",
        Event.event_type == "dns_query",
        Event.source_ip == event.source_ip,
        Event.timestamp >= since,
        Event.timestamp <= event.timestamp,
    )
    count = db.scalar(stmt) or 0

    if count < threshold:
        return None
    if has_recent_open_alert(
        db, "dns_anomaly", source_ip=event.source_ip, within_minutes=window_seconds / 60
    ):
        return None

    contributing_ids = list(
        db.scalars(
            select(Event.id).where(
                Event.source == "dns",
                Event.event_type == "dns_query",
                Event.source_ip == event.source_ip,
                Event.timestamp >= since,
                Event.timestamp <= event.timestamp,
            )
        )
    )

    return make_alert(
        db,
        rule_key="dns_anomaly",
        rule_name=rule.name,
        title=f"Anomalous DNS query volume from {event.source_ip}",
        severity=Severity.MEDIUM,
        detected_at=event.timestamp,
        triggering_event_ids=contributing_ids,
        username=event.username,
        source_ip=event.source_ip,
        hostname=event.hostname,
        metadata={"query_count": count, "window_seconds": window_seconds},
    )
