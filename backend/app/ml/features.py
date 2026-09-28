"""
Feature engineering: Event rows -> one feature vector per
(source_ip, time window).

The 10 features are exactly the ones named in the project spec:
login_frequency, failed_login_count, request_frequency, bytes_sent,
bytes_received, unique_destination_count, dns_request_count,
connection_count, process_frequency, login_hour.

Honesty note: none of our synthetic scenarios currently emit an
inbound byte volume, so `bytes_received` is always 0 for now — it's
included because the spec names it, and will show real variance once
a scenario models inbound traffic. We do not fabricate a value for it.
"""

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event

FEATURE_COLUMNS = [
    "login_frequency",
    "failed_login_count",
    "request_frequency",
    "bytes_sent",
    "bytes_received",
    "unique_destination_count",
    "dns_request_count",
    "connection_count",
    "process_frequency",
    "login_hour",
]


def _floor_to_window(ts: datetime, window_minutes: int) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    epoch_minutes = int(ts.timestamp() // 60)
    floored_minutes = (epoch_minutes // window_minutes) * window_minutes
    return datetime.fromtimestamp(floored_minutes * 60, tz=timezone.utc)


def build_feature_matrix(db: Session, window_minutes: int = 5) -> pd.DataFrame:
    """Returns a DataFrame with columns [source_ip, window_start,
    *FEATURE_COLUMNS]. One row per source_ip that had at least one
    event in that window."""
    events = list(db.scalars(select(Event).where(Event.source_ip.is_not(None))))

    rows = []
    for e in events:
        rows.append({
            "source_ip": e.source_ip,
            "window_start": _floor_to_window(e.timestamp, window_minutes),
            "source": e.source,
            "event_type": e.event_type,
            "status": e.status,
            "destination_ip": e.destination_ip,
            "hour": e.timestamp.hour,
            "bytes_sent": (e.event_metadata or {}).get("bytes_sent") or 0,
            "bytes_received": (e.event_metadata or {}).get("bytes_received") or 0,
        })

    if not rows:
        return pd.DataFrame(columns=["source_ip", "window_start"] + FEATURE_COLUMNS)

    df = pd.DataFrame(rows)

    def agg_group(g: pd.DataFrame) -> pd.Series:
        is_login = g["event_type"] == "login"
        return pd.Series({
            "login_frequency": int(is_login.sum()),
            "failed_login_count": int((is_login & (g["status"] == "failed")).sum()),
            "request_frequency": int(len(g)),
            "bytes_sent": float(g["bytes_sent"].sum()),
            "bytes_received": float(g["bytes_received"].sum()),
            "unique_destination_count": int(g["destination_ip"].nunique()),
            "dns_request_count": int((g["event_type"] == "dns_query").sum()),
            "connection_count": int((g["source"] == "network").sum()),
            "process_frequency": int((g["event_type"] == "process_execution").sum()),
            "login_hour": int(g["hour"].iloc[0]),
        })

    grouped = (
        df.groupby(["source_ip", "window_start"], as_index=False)
        .apply(agg_group, include_groups=False)
    )
    return grouped.reset_index(drop=True)
