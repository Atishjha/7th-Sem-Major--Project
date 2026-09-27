"""
Alert: the output of the detection engine. One row per rule match.

`triggering_event_ids` keeps the raw evidence trail (which Event rows
caused this alert) so later phases (correlation, incidents, the AI
analyst) can pull the full context without re-deriving it. Denormalized
username/source_ip/hostname/severity are copied from the triggering
event so the Alerts UI never needs a join for the common case.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import Severity


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    rule_key: Mapped[str] = mapped_column(String(64), index=True)
    rule_name: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[Severity] = mapped_column(default=Severity.MEDIUM, index=True)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | closed

    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    hostname: Mapped[str | None] = mapped_column(String(64), nullable=True)

    triggering_event_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    alert_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, name="metadata"
    )

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
