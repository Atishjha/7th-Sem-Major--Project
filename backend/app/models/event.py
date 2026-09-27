"""
Normalized security event.

Matches the event schema in the project spec exactly (event_id,
timestamp, source, source_ip, destination_ip, username, hostname,
event_type, action, status, severity, message, metadata). `id` is an
internal autoincrement PK; `event_id` is the human-readable
"EVT-000123" identifier shown in the UI, assigned right after insert
so it can incorporate the real row id.

All data produced by the event simulator (Phase 4) is synthetic —
IPs are drawn from IANA documentation ranges (RFC 5737 / RFC 2606)
that can never resolve to a real host.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import Severity


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)  # authentication | endpoint | network | dns
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    destination_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    hostname: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))  # success | failed | n/a
    severity: Mapped[Severity] = mapped_column(default=Severity.LOW)
    message: Mapped[str] = mapped_column(String(255))
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, name="metadata"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_events_source_ip_timestamp", "source_ip", "timestamp"),
        Index("ix_events_username_timestamp", "username", "timestamp"),
    )
