from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '19b9f52a0273'
down_revision: Union[str, None] = 'e6dc5ec734c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('hostname', sa.String(length=64), nullable=False),
        sa.Column(
            'criticality',
            postgresql.ENUM(
                'LOW',
                'MEDIUM',
                'HIGH',
                'CRITICAL',
                name='severity',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hostname'),
    )

    op.create_index(
        'ix_assets_hostname',
        'assets',
        ['hostname'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_assets_hostname', table_name='assets')
    op.drop_table('assets')
