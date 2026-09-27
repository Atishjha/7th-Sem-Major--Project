"""
Shared helpers used by every rule module.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.common import Severity
from app.utils.ids import next_alert_id
def has_recent_open_alert(
    db: Session,
    rule_key: str,
    *,
    source_ip: str | None = None,
    username: str | None = None,
    within_minutes: int = 5,
) -> bool:
    """Debounce: don't spam a new alert every time a threshold is still
    exceeded (e.g. failed login #6, #7, #8 of the same burst)."""
    since = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)
    stmt = select(Alert).where(Alert.rule_key == rule_key, Alert.detected_at >= since)
    if source_ip is not None:
        stmt = stmt.where(Alert.source_ip == source_ip)
    if username is not None:
        stmt = stmt.where(Alert.username == username)
    return db.scalar(stmt) is not None
def make_alert(
    db: Session,
    *,
    rule_key: str,
    rule_name: str,
    title: str,
    severity: Severity,
    detected_at: datetime,
    triggering_event_ids: list[int],
    username: str | None = None,
    source_ip: str | None = None,
    hostname: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Alert:
    alert_id_num, alert_id_str = next_alert_id(db)
    alert = Alert(
        id=alert_id_num,
        alert_id=alert_id_str,
        rule_key=rule_key,
        rule_name=rule_name,
        title=title,
        severity=severity,
        status="open",
        username=username,
        source_ip=source_ip,
        hostname=hostname,
        triggering_event_ids=triggering_event_ids,
        alert_metadata=metadata or {},
        detected_at=detected_at,
    )
    db.add(alert)
    return alert
