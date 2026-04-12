"""Sprint 17 tables: reward density, wallet profiles/signals, aggregated signals, lifecycle events.

Revision ID: 014
Revises: 005
Create Date: 2026-04-11
"""

from alembic import op

revision = "014"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reward density scores (hypertable)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pm.reward_density_scores (
            score_id    UUID DEFAULT gen_random_uuid() NOT NULL,
            market_id   TEXT NOT NULL,
            scored_at   TIMESTAMPTZ NOT NULL,
            score       JSONB NOT NULL,
            PRIMARY KEY (score_id, scored_at)
        );
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'pm.reward_density_scores', 'scored_at',
            if_not_exists => TRUE
        );
        """
    )

    # Wallet profiles (regular table — point-in-time snapshots)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pm.wallet_profiles (
            wallet_address  TEXT NOT NULL,
            profiled_at     TIMESTAMPTZ NOT NULL,
            profile         JSONB NOT NULL,
            cluster_id      INTEGER,
            PRIMARY KEY (wallet_address, profiled_at)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_pm_wallet_profiles_profiled_at
            ON pm.wallet_profiles(profiled_at DESC);
        """
    )

    # Wallet signals (hypertable)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pm.wallet_signals (
            signal_id   UUID DEFAULT gen_random_uuid() NOT NULL,
            market_id   TEXT NOT NULL,
            computed_at TIMESTAMPTZ NOT NULL,
            signal      JSONB NOT NULL,
            PRIMARY KEY (signal_id, computed_at)
        );
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'pm.wallet_signals', 'computed_at',
            if_not_exists => TRUE
        );
        """
    )

    # Aggregated signals (hypertable)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pm.aggregated_signals (
            signal_id       UUID DEFAULT gen_random_uuid() NOT NULL,
            market_id       TEXT NOT NULL,
            aggregated_at   TIMESTAMPTZ NOT NULL,
            signal          JSONB NOT NULL,
            PRIMARY KEY (signal_id, aggregated_at)
        );
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'pm.aggregated_signals', 'aggregated_at',
            if_not_exists => TRUE
        );
        """
    )

    # Lifecycle events (regular table — audit log)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pm.lifecycle_events (
            event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            strategy_id     TEXT NOT NULL,
            event_type      TEXT NOT NULL,
            triggered_at    TIMESTAMPTZ NOT NULL,
            rule_id         TEXT NOT NULL,
            approved        BOOLEAN,
            approved_at     TIMESTAMPTZ,
            notes           TEXT
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_pm_lifecycle_events_strategy_time
            ON pm.lifecycle_events(strategy_id, triggered_at DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_pm_lifecycle_events_type_time
            ON pm.lifecycle_events(event_type, triggered_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pm.lifecycle_events;")
    op.execute("DROP TABLE IF EXISTS pm.aggregated_signals;")
    op.execute("DROP TABLE IF EXISTS pm.wallet_signals;")
    op.execute("DROP TABLE IF EXISTS pm.wallet_profiles;")
    op.execute("DROP TABLE IF EXISTS pm.reward_density_scores;")
