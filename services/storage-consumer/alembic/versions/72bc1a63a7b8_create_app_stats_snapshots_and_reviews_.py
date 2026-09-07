"""create app_stats_snapshots and reviews tables

Revision ID: 72bc1a63a7b8
Revises:
Create Date: 2026-09-07 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72bc1a63a7b8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # app_id is a plain indexed integer on both tables, not a foreign key:
    # the `apps` table it logically references belongs to
    # app-list-api-fastapi's own migration history (see README.md).
    op.create_table(
        'app_stats_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('app_id', sa.Integer(), nullable=False),
        sa.Column('min_installs', sa.BigInteger(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('ratings', sa.BigInteger(), nullable=True),
        sa.Column('reviews_count', sa.BigInteger(), nullable=True),
        sa.Column('store_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.String(length=100), nullable=True),
        sa.Column('ad_supported', sa.Boolean(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_app_stats_snapshots_app_id'), 'app_stats_snapshots', ['app_id'], unique=False
    )

    op.create_table(
        'reviews',
        sa.Column('review_id', sa.String(length=255), nullable=False),
        sa.Column('app_id', sa.Integer(), nullable=False),
        sa.Column('at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_name', sa.String(length=255), nullable=True),
        sa.Column('thumbs_up_count', sa.Integer(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('sentiment', sa.String(length=50), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('review_id'),
    )
    op.create_index(op.f('ix_reviews_app_id'), 'reviews', ['app_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reviews_app_id'), table_name='reviews')
    op.drop_table('reviews')
    op.drop_index(op.f('ix_app_stats_snapshots_app_id'), table_name='app_stats_snapshots')
    op.drop_table('app_stats_snapshots')
