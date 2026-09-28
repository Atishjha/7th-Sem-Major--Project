"""
Incident: a group of correlated alerts (Phase 7).

Every alert belongs to exactly one incident. `incident_metadata`
keeps the transparent correlation trail — the entity sets seen so
far, the rule keys involved, and, per alert, the score and human-
readable reasons it was attached — so the "why were these grouped?"
question always has a concrete answer (useful for the viva and for
the AI analyst in Phase 10).

`risk_score` stays NULL until the Risk Engine exists (Phase 8).
"""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, DateTime, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.models.common import Severity
class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    incident_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[Severity] = mapped_column(default=Severity.MEDIUM, index=True)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    primary_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    primary_source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    primary_hostname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    alert_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    incident_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, name="metadata"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
class IncidentEvent(Base):
    """Junction: which raw events back an incident (union of its alerts'
    triggering events)."""
    __tablename__ = "incident_events"
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id"), primary_key=True, index=True
    )
