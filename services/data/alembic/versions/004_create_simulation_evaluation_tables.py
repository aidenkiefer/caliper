"""Create pm.simulation_runs, pm.evaluation_reports, pm.simulation_validation tables.

Revision ID: 004
Revises: 003
Create Date: 2026-04-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003_pm_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE pm.simulation_runs (
            run_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            strategy_id   TEXT NOT NULL,
            market_id     TEXT NOT NULL,
            started_at    TIMESTAMPTZ NOT NULL,
            completed_at  TIMESTAMPTZ,
            config        JSONB NOT NULL,
            result        JSONB
        )
    """))

    op.execute(sa.text("""
        CREATE INDEX ix_simulation_runs_strategy
            ON pm.simulation_runs(strategy_id)
    """))

    op.execute(sa.text("""
        CREATE INDEX ix_simulation_runs_started
            ON pm.simulation_runs(started_at DESC)
    """))

    op.execute(sa.text("""
        CREATE TABLE pm.evaluation_reports (
            report_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            generated_at  TIMESTAMPTZ NOT NULL,
            period_start  TIMESTAMPTZ NOT NULL,
            period_end    TIMESTAMPTZ NOT NULL,
            report        JSONB NOT NULL
        )
    """))

    op.execute(sa.text("""
        CREATE INDEX ix_evaluation_reports_generated
            ON pm.evaluation_reports(generated_at DESC)
    """))

    op.execute(sa.text("""
        CREATE TABLE pm.simulation_validation (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id          UUID REFERENCES pm.simulation_runs(run_id),
            validated_at    TIMESTAMPTZ NOT NULL,
            fill_rate_sim   DECIMAL,
            fill_rate_real  DECIMAL,
            slippage_mean   DECIMAL,
            slippage_std    DECIMAL,
            pnl_correlation DECIMAL,
            determinism_ok  BOOLEAN
        )
    """))

    op.execute(sa.text("""
        CREATE INDEX ix_simulation_validation_run
            ON pm.simulation_validation(run_id)
    """))


def downgrade() -> None:
    # Drop in reverse order of dependencies
    op.execute(sa.text("DROP TABLE IF EXISTS pm.simulation_validation"))
    op.execute(sa.text("DROP TABLE IF EXISTS pm.evaluation_reports"))
    op.execute(sa.text("DROP TABLE IF EXISTS pm.simulation_runs"))
