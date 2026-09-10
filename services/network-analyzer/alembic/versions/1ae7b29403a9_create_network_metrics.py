"""create network_metrics

Revision ID: 1ae7b29403a9
Revises:
Create Date: 2026-09-10 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ae7b29403a9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # app_id is a plain indexed integer, not a foreign key: the `apps` table
    # it logically references belongs to app-list-api-fastapi's own
    # migration history (see README.md).
    op.create_table(
        'network_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('app_id', sa.Integer(), nullable=False),
        sa.Column('scenario', sa.String(length=10), nullable=False),
        sa.Column('source_file', sa.String(length=255), nullable=False),
        sa.Column('handshake_rtt_ms', sa.Float(), nullable=True),
        sa.Column('retransmission_count', sa.Integer(), nullable=False),
        sa.Column('zero_window_event_count', sa.Integer(), nullable=False),
        sa.Column('tcp_reset_drops', sa.Integer(), nullable=False),
        sa.Column('total_transferred_bytes', sa.BigInteger(), nullable=False),
        sa.Column('total_payload_bytes', sa.BigInteger(), nullable=False),
        sa.Column('overhead_ratio', sa.Float(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_network_metrics_app_id'), 'network_metrics', ['app_id'], unique=False)
    op.create_index(op.f('ix_network_metrics_source_file'), 'network_metrics', ['source_file'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_network_metrics_source_file'), table_name='network_metrics')
    op.drop_index(op.f('ix_network_metrics_app_id'), table_name='network_metrics')
    op.drop_table('network_metrics')
