"""
Asset: hostnames with a criticality tier, feeding the Risk Engine's
"Asset Criticality" factor. Reuses the Severity enum for the tier
scale (low/medium/high/critical) — criticality and severity share the
same 4-point scale, and reusing it avoids a second enum type.

Any hostname not in this table (e.g. a freshly-generated demo host)
falls back to a documented default tier rather than silently scoring
zero — see DEFAULT_CRITICALITY in risk_engine.py.
"""

from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import Severity


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hostname: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    criticality: Mapped[Severity] = mapped_column(default=Severity.MEDIUM)
    description: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )