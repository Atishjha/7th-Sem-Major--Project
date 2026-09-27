"""
Rule 3 — Impossible Travel.

Same user: Location A -> Location B within an unrealistic time window.

Approximation note: this project has no real geo-IP dataset, so we
don't compute actual distance/speed physics. Instead we treat a
"new_location" event as the location-change signal and check whether
a successful login for the same user happened within the configured
window beforehand — a common simplified version of this rule, and an
honest one given the synthetic data available here.
"""
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.detectors.common import has_recent_open_alert, make_alert
from app.models.common import Severity
from app.models.detection_rule import DetectionRule
from app.models.event import Event
def check(db: Session, event: Event, rule: DetectionRule):
    if event.source != "authentication" or event.event_type != "new_location":
        return None
    if not event.username:
        return None
    window_minutes = rule.config.get("window_minutes", 10)
    since = event.timestamp - timedelta(minutes=window_minutes)
    prior_login = db.scalar(
        select(Event)
        .where(
            Event.source == "authentication",
            Event.event_type == "login",
            Event.status == "success",
            Event.username == event.username,
            Event.timestamp >= since,
            Event.timestamp < event.timestamp,
        )
        .order_by(Event.timestamp.desc())
        .limit(1)
    )
    if prior_login is None:
        return None
    if has_recent_open_alert(
        db, "impossible_travel", username=event.username, within_minutes=window_minutes
    ):
        return None
    return make_alert(
        db,
        rule_key="impossible_travel",
        rule_name=rule.name,
        title=f"Impossible travel detected for {event.username}",
        severity=Severity.HIGH,
        detected_at=event.timestamp,
        triggering_event_ids=[prior_login.id, event.id],
        username=event.username,
        source_ip=event.source_ip,
        hostname=event.hostname,
        metadata={
            "observed_location": event.event_metadata.get("observed_location"),
            "usual_location": event.event_metadata.get("usual_location"),
            "minutes_since_prior_login": round(
                (event.timestamp - prior_login.timestamp).total_seconds() / 60, 2
            ),
        },
    )
