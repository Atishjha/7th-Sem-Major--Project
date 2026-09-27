"""
Configurable detection rule. One row per rule (brute_force,
suspicious_powershell, impossible_travel, dns_anomaly,
abnormal_network). `config` holds the rule's own tunable thresholds
as JSON so they can be changed via the API without a code change or
redeploy.
"""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
class DetectionRule(Base):
    __tablename__ = "detection_rules"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
