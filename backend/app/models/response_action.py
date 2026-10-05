"""
ResponseAction: one row per recommended/decided response action.

Lifecycle is two-step, matching the spec's flow collapsed to how an
analyst actually experiences it: "recommended" (AI suggested it, not
yet acted on) -> "rejected" (no action taken) or "simulated_success"
(approval and mock execution happen as one atomic step — there's
nothing for a real system to actually do, so there's no separate
pending-execution state). Never executes anything on a real system;
result_message always says so explicitly.
"""

import enum

from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ActionType(str, enum.Enum):
    DISABLE_ACCOUNT = "disable_account"
    REVOKE_SESSION = "revoke_session"
    ISOLATE_ENDPOINT = "isolate_endpoint"
    BLOCK_INDICATOR = "block_indicator"
    RESET_CREDENTIALS = "reset_credentials"
    CREATE_FIREWALL_RULE = "create_firewall_rule"


class ActionStatus(str, enum.Enum):
    RECOMMENDED = "recommended"
    REJECTED = "rejected"
    SIMULATED_SUCCESS = "simulated_success"


class ResponseAction(Base):
    __tablename__ = "response_actions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    response_id: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id"),
        index=True,
    )

    action_type: Mapped[ActionType] = mapped_column(
        SAEnum(
            ActionType,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            name="actiontype",
        ),
        index=True,
    )

    target: Mapped[str] = mapped_column(
        String(128)
    )

    recommended_reason: Mapped[str] = mapped_column(
        String(255)
    )

    status: Mapped[ActionStatus] = mapped_column(
        SAEnum(
            ActionStatus,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            name="actionstatus",
        ),
        default=ActionStatus.RECOMMENDED,
        index=True,
    )

    result_message: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    decided_by_username: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

