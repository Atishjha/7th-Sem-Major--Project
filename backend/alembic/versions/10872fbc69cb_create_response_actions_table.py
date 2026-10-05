"""create response actions table

Revision ID: 10872fbc69cb
Revises: 19b9f52a0273
Create Date: 2026-10-04 14:11:19.050688

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "10872fbc69cb"
down_revision: Union[str, None] = "19b9f52a0273"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    action_type = sa.Enum(
        "disable_account",
        "revoke_session",
        "isolate_endpoint",
        "block_indicator",
        "reset_credentials",
        "create_firewall_rule",
        name="actiontype",
    )

    action_status = sa.Enum(
        "recommended",
        "rejected",
        "simulated_success",
        name="actionstatus",
    )


    op.create_table(
        "response_actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("response_id", sa.String(length=20), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("action_type", action_type, nullable=False),
        sa.Column("target", sa.String(length=128), nullable=False),
        sa.Column("recommended_reason", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            action_status,
            nullable=False,
            server_default="recommended",
        ),
        sa.Column("result_message", sa.String(length=255), nullable=True),
        sa.Column(
            "decided_by_username",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        
    )

    op.create_index(
        "ix_response_actions_response_id",
        "response_actions",
        ["response_id"],
        unique=True,
    )

    op.create_index(
        "ix_response_actions_incident_id",
        "response_actions",
        ["incident_id"],
        unique=False,
    )

    op.create_index(
        "ix_response_actions_action_type",
        "response_actions",
        ["action_type"],
        unique=False,
    )

    op.create_index(
        "ix_response_actions_status",
        "response_actions",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_response_actions_created_at",
        "response_actions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_response_actions_created_at",
        table_name="response_actions",
    )
    op.drop_index(
        "ix_response_actions_status",
        table_name="response_actions",
    )
    op.drop_index(
        "ix_response_actions_action_type",
        table_name="response_actions",
    )
    op.drop_index(
        "ix_response_actions_incident_id",
        table_name="response_actions",
    )
    op.drop_index(
        "ix_response_actions_response_id",
        table_name="response_actions",
    )

    op.drop_table("response_actions")

    sa.Enum(
        "recommended",
        "rejected",
        "simulated_success",
        name="actionstatus",
    ).drop(op.get_bind(), checkfirst=True)

    sa.Enum(
        "disable_account",
        "revoke_session",
        "isolate_endpoint",
        "block_indicator",
        "reset_credentials",
        "create_firewall_rule",
        name="actiontype",
    ).drop(op.get_bind(), checkfirst=True)