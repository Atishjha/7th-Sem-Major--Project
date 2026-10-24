"""Plain helper functions shared by several test modules."""

from datetime import datetime, timedelta, timezone

from app.detectors.engine import run_detectors
from app.models.common import Severity
from app.models.event import Event
from app.services.correlation import correlate_alerts
from app.services.event_scenarios import SCENARIOS
from app.services.risk_engine import recompute_and_save
from app.utils.ids import next_event_id


def now() -> datetime:
    return datetime.now(timezone.utc)


def make_event(
    db,
    *,
    source: str,
    event_type: str,
    ts: datetime | None = None,
    status: str = "n/a",
    action: str = "test",
    severity: Severity = Severity.LOW,
    message: str = "test event",
    source_ip: str | None = None,
    destination_ip: str | None = None,
    username: str | None = None,
    hostname: str | None = None,
    metadata: dict | None = None,
) -> Event:
    event_pk, event_label = next_event_id(db)
    event = Event(
        id=event_pk, event_id=event_label, timestamp=ts or now(),
        source=source, event_type=event_type, action=action, status=status,
        severity=severity, message=message, source_ip=source_ip,
        destination_ip=destination_ip, username=username, hostname=hostname,
        event_metadata=metadata or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def failed_login(db, ip="203.0.113.25", user="demo_user", host="WIN-CLIENT-01", ts=None):
    return make_event(
        db, source="authentication", event_type="login", status="failed",
        source_ip=ip, username=user, hostname=host, ts=ts,
        message=f"Failed login for {user}",
    )


def successful_login(db, user="demo_user", ip="192.168.56.10", host="WIN-CLIENT-01", ts=None):
    return make_event(
        db, source="authentication", event_type="login", status="success",
        source_ip=ip, username=user, hostname=host, ts=ts,
        message=f"Login for {user}",
    )


def ingest(db, event: Event):
    """Exactly what SimulatorRunner._run does for each new event:
    detect -> correlate -> score. Returns (alerts, [(incident, created)])."""
    alerts = run_detectors(db, event)
    touched = []
    if alerts:
        touched = correlate_alerts(db, alerts)
        for incident, _created in touched:
            recompute_and_save(db, incident)
        db.commit()
        for incident, _created in touched:
            db.refresh(incident)
    return alerts, touched


def replay_scenario(db, key: str):
    """Run one of the real demo scenarios through the full pipeline without
    the live sleeps (the simulator's delays only make the UI feel live; the
    clock still advances by each event's delay so time-window rules behave
    exactly as they do in the real run)."""
    clock = now()
    all_alerts, incidents = [], {}
    for delay, fields in SCENARIOS[key]():
        clock = clock + timedelta(seconds=delay)
        event_pk, event_label = next_event_id(db)
        event = Event(id=event_pk, event_id=event_label, timestamp=clock, **fields)
        db.add(event)
        db.commit()
        db.refresh(event)
        alerts, touched = ingest(db, event)
        all_alerts.extend(alerts)
        for incident, _created in touched:
            incidents[incident.id] = incident
    return all_alerts, list(incidents.values())
