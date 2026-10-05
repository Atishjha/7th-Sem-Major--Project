"""
Assembles everything an AI provider needs to investigate an incident
— incident, its alerts, its linked events (the Timeline/Evidence an
analyst would read), the risk breakdown, and the MITRE mapping for
the rules involved — into one plain dict. Both the mock and real
providers receive exactly this, so the mock's output is built from
the same facts a real LLM would be given, not a shortcut subset.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.incident import Incident, IncidentEvent
from app.services.mitre_mapping import techniques_for_rules


def build_context(db: Session, incident: Incident, alerts: list) -> dict:
    events = list(
        db.scalars(
            select(Event)
            .join(IncidentEvent, IncidentEvent.event_id == Event.id)
            .where(IncidentEvent.incident_id == incident.id)
            .order_by(Event.timestamp)
        )
    )
    meta = incident.incident_metadata or {}
    rule_keys = meta.get("rule_keys", [])

    indicators = sorted(
        {e.source_ip for e in events if e.source_ip}
        | {e.destination_ip for e in events if e.destination_ip}
    )

    return {
        "incident": {
            "incident_id": incident.incident_id,
            "title": incident.title,
            "incident_type": incident.incident_type,
            "severity": incident.severity.value,
            "status": incident.status,
            "primary_username": incident.primary_username,
            "primary_source_ip": incident.primary_source_ip,
            "primary_hostname": incident.primary_hostname,
            "first_seen": incident.first_seen.isoformat(),
            "last_seen": incident.last_seen.isoformat(),
            "alert_count": incident.alert_count,
            "risk_score": incident.risk_score,
            "risk_breakdown": meta.get("risk_breakdown", []),
            "entities": meta.get("entities", {}),
            "rule_keys": rule_keys,
        },
        "alerts": [
            {
                "alert_id": a.alert_id,
                "rule_key": a.rule_key,
                "rule_name": a.rule_name,
                "title": a.title,
                "severity": a.severity.value,
                "detected_at": a.detected_at.isoformat(),
                "username": a.username,
                "source_ip": a.source_ip,
                "hostname": a.hostname,
                "metadata": a.alert_metadata,
            }
            for a in alerts
        ],
        "events": [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "source": e.source,
                "event_type": e.event_type,
                "status": e.status,
                "severity": e.severity.value,
                "message": e.message,
                "username": e.username,
                "source_ip": e.source_ip,
                "destination_ip": e.destination_ip,
                "hostname": e.hostname,
                "metadata": e.event_metadata,
            }
            for e in events
        ],
        "indicators": indicators,
        "mitre_mapping": techniques_for_rules(db, rule_keys),
    }
