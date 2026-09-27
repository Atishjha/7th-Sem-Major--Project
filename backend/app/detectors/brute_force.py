"""
Rule 1 — Brute Force.

IF failed_login_count >= threshold within window_minutes from the
same source IP THEN generate an alert.
"""
from datetime import timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.detectors.common import has_recent_open_alert, make_alert
from app.models.common import Severity
from app.models.detection_rule import DetectionRule
from app.models.event import Event
def check(db: Session, event: Event, rule: DetectionRule):
    if event.source != "authentication" or event.event_type != "login":
        return None
    if event.status != "failed" or not event.source_ip:
        return None
    threshold = rule.config.get("failed_threshold", 5)
    window_minutes = rule.config.get("window_minutes", 5)
    since = event.timestamp - timedelta(minutes=window_minutes)
    stmt = select(func.count(), func.min(Event.id)).where(
        Event.source == "authentication",
        Event.event_type == "login",
        Event.status == "failed",
        Event.source_ip == event.source_ip,
        Event.timestamp >= since,
        Event.timestamp <= event.timestamp,
    )
    count, _ = db.execute(stmt).one()
    if count < threshold:
        return None
    if has_recent_open_alert(
        db, "brute_force", source_ip=event.source_ip, within_minutes=window_minutes
    ):
        return None
    contributing_ids = list(
        db.scalars(
            select(Event.id).where(
                Event.source == "authentication",
                Event.event_type == "login",
                Event.status == "failed",
                Event.source_ip == event.source_ip,
                Event.timestamp >= since,
                Event.timestamp <= event.timestamp,
            )
        )
    )
    return make_alert(
        db,
        rule_key="brute_force",
        rule_name=rule.name,
        title=f"Brute force login attempts from {event.source_ip}",
        severity=Severity.HIGH,
        detected_at=event.timestamp,
        triggering_event_ids=contributing_ids,
        username=event.username,
        source_ip=event.source_ip,
        hostname=event.hostname,
        metadata={"failed_count": count, "window_minutes": window_minutes},
    )
