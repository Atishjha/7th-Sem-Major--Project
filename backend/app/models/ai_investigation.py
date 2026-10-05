"""
AI Investigation: a saved analyst report for an incident. One row per
investigation run — POST /api/incidents/{id}/investigate always
creates a new one (history), GET fetches the most recent.
`provider_used` records which provider actually produced it (e.g.
"mock" or "mock (llm_failed: <reason>)" on fallback), so it's always
clear whether a given report is deterministic-offline or LLM-backed.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AIInvestigation(Base):
    __tablename__ = "ai_investigations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    provider_used: Mapped[str] = mapped_column(String(64))
    investigation: Mapped[dict[str, Any]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
