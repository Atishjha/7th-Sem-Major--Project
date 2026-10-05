"""
ID helpers.

`events.event_id` is NOT NULL, so we can't insert a row and fill in
event_id afterwards. Instead we pre-fetch the row's future `id` from
Postgres's own sequence and set both `id` and `event_id` before the
row is ever inserted — one round trip, one INSERT, no flush/update
dance.
"""

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.common import Severity


def next_event_id(db: Session) -> tuple[int, str]:
    next_id = db.execute(text("SELECT nextval('events_id_seq')")).scalar_one()
    return next_id, f"EVT-{next_id:06d}"


def next_alert_id(db: Session) -> tuple[int, str]:
    next_id = db.execute(text("SELECT nextval('alerts_id_seq')")).scalar_one()
    return next_id, f"ALT-{next_id:06d}"


def next_incident_id(db: Session) -> tuple[int, str]:
    """Human-readable ids start at INC-1001, matching the spec's example."""
    next_id = db.execute(text("SELECT nextval('incidents_id_seq')")).scalar_one()
    return next_id, f"INC-{1000 + next_id}"


def next_response_id(db: Session) -> tuple[int, str]:
    next_id = db.execute(text("SELECT nextval('response_actions_id_seq')")).scalar_one()
    return next_id, f"RESP-{next_id:06d}"


def parse_severity(value: str) -> Severity:
    """Convert a lowercase query-string value ("critical") into the
    Severity enum member, so filters compare enum-to-enum rather than
    a raw string against a native Postgres enum column (which stores
    the member's NAME, e.g. 'CRITICAL', not its value)."""
    try:
        return Severity(value.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity '{value}'. Expected one of: "
            f"{', '.join(s.value for s in Severity)}",
        )
