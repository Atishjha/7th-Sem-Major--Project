"""
Rule 2 — Suspicious PowerShell.

Detects synthetic PowerShell events whose metadata already carries a
`pattern_matched` marker (set by the event simulator's scenario
generator to represent e.g. a hidden-window flag) for the configured
process name.
"""
from sqlalchemy.orm import Session
from app.detectors.common import make_alert
from app.models.common import Severity
from app.models.detection_rule import DetectionRule
from app.models.event import Event
def check(db: Session, event: Event, rule: DetectionRule):
    if event.source != "endpoint" or event.event_type != "process_execution":
        return None
    flagged_process = rule.config.get("flagged_process", "powershell.exe")
    process = event.event_metadata.get("process")
    pattern = event.event_metadata.get("pattern_matched")
    if process != flagged_process or not pattern:
        return None
    return make_alert(
        db,
        rule_key="suspicious_powershell",
        rule_name=rule.name,
        title=f"Suspicious PowerShell command pattern on {event.hostname}",
        severity=Severity.HIGH,
        detected_at=event.timestamp,
        triggering_event_ids=[event.id],
        username=event.username,
        source_ip=event.source_ip,
        hostname=event.hostname,
        metadata={
            "pattern_matched": pattern,
            "command_line": event.event_metadata.get("command_line"),
        },
    )
