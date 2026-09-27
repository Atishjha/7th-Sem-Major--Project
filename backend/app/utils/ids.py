"""
ID helpers.

`events.event_id` is NOT NULL, so we can't insert a row and fill in
event_id afterwards. Instead we pre-fetch the row's future `id` from
Postgres's own sequence and set both `id` and `event_id` before the
row is ever inserted — one round trip, one INSERT, no flush/update
dance.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session
def next_event_id(db: Session) -> tuple[int, str]:
    next_id = db.execute(text("SELECT nextval('events_id_seq')")).scalar_one()
    return next_id, f"EVT-{next_id:06d}"
