"""Create pm.features TimescaleDB hypertable for feature snapshots

Revision ID: 003_pm_features
Revises: 002_polymarket_schema
Create Date: 2026-04-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_pm_features'
down_revision: Union[str, None] = '002_polymarket_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # pm.features — HYPERTABLE on captured_at for feature snapshots
    # Stores serialized FeatureSnapshot as JSONB with typed fields for queries
    # -------------------------------------------------------------------------
    op.create_table(
        'features',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('market_id', sa.Text(), nullable=False),
        sa.Column('token_id', sa.Text(), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('features', postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint('id', 'captured_at'),  # TimescaleDB requires time column in PK
        schema='pm'
    )

    # Convert to TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('pm.features', 'captured_at', "
        "if_not_exists => TRUE)"
    )

    # Index for efficient queries by market_id and time
    op.create_index(
        'ix_pm_features_market_id_captured_at',
        'features',
        ['market_id', sa.text('captured_at DESC')],
        schema='pm',
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_pm_features_market_id_captured_at', table_name='features', schema='pm')

    # Drop the hypertable
    op.execute("DROP TABLE IF EXISTS pm.features")
