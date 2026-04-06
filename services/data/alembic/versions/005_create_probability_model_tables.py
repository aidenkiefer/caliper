"""Create pm.probability_predictions, pm.lag_test_results, pm.calibration_reports tables.

Revision ID: 005
Revises: 004
Create Date: 2026-04-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE pm.probability_predictions (
            record_id      TEXT NOT NULL DEFAULT gen_random_uuid()::text,
            market_id      TEXT NOT NULL,
            token_id       TEXT NOT NULL,
            predicted_at   TIMESTAMPTZ NOT NULL,
            p_hat          DECIMAL NOT NULL,
            implied_prob   DECIMAL NOT NULL,
            mispricing     DECIMAL NOT NULL,
            threshold_met  BOOLEAN NOT NULL,
            model_version  TEXT NOT NULL,
            PRIMARY KEY (record_id, predicted_at)
        )
    """))

    op.execute(sa.text("""
        SELECT create_hypertable('pm.probability_predictions', 'predicted_at')
    """))

    op.execute(sa.text("""
        CREATE TABLE pm.lag_test_results (
            test_id        TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            run_at         TIMESTAMPTZ NOT NULL,
            test_type      TEXT NOT NULL,
            period_start   TIMESTAMPTZ NOT NULL,
            period_end     TIMESTAMPTZ NOT NULL,
            results        JSONB NOT NULL
        )
    """))

    op.execute(sa.text("""
        CREATE TABLE pm.calibration_reports (
            report_id      TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            generated_at   TIMESTAMPTZ NOT NULL,
            model_version  TEXT NOT NULL,
            brier_score    DECIMAL NOT NULL,
            ece            DECIMAL NOT NULL,
            auc            DECIMAL,
            reliability    JSONB NOT NULL,
            needs_recal    BOOLEAN NOT NULL
        )
    """))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS pm.calibration_reports"))
    op.execute(sa.text("DROP TABLE IF EXISTS pm.lag_test_results"))
    op.execute(sa.text("DROP TABLE IF EXISTS pm.probability_predictions"))
