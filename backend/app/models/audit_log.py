"""
AuditLog: one row per privileged, state-changing action in the
system. `action`/`resource_type`/`result` are free-text strings, not
enums — unlike Severity (a genuine fixed 4-value domain), the set of
audited action types will keep growing as the system grows, and a
new enum migration for every new action type would be the wrong
tool. `resource_id` matches the spec's own example exactly: for a
response-action decision it's the INCIDENT's id (e.g. "INC-1001"),
not the response action's own id — that's what lets the Incident
Page's Audit tab show everything relevant to one incident with a
single filter.
"""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    username: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(255))
    resource_type: Mapped[str] = mapped_column(String(32), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result: Mapped[str] = mapped_column(String(16), default="SUCCESS")
