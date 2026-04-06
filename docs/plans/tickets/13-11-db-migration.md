# Ticket 13-11: DB Migration

## Task

Create Alembic migration `004_create_simulation_evaluation_tables.py` adding three new tables to the `pm` schema: `pm.simulation_runs`, `pm.evaluation_reports`, and `pm.simulation_validation`.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/data/alembic/versions/004_create_simulation_evaluation_tables.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ Database Tables)
- `services/data/alembic/versions/003_create_pm_features_hypertable.py` (migration patterns)
- `services/data/alembic/versions/002_create_polymarket_schema.py` (pm schema patterns)

## Done criteria

### Migration file: `004_create_simulation_evaluation_tables.py`

**Revision metadata:**
- `revision = "004"`
- `down_revision = "003"`
- `branch_labels = None`, `depends_on = None`

**`upgrade()` creates:**

```sql
CREATE TABLE pm.simulation_runs (
    run_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id   TEXT NOT NULL,
    market_id     TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL,
    completed_at  TIMESTAMPTZ,
    config        JSONB NOT NULL,
    result        JSONB
);

CREATE INDEX ix_simulation_runs_strategy ON pm.simulation_runs(strategy_id);
CREATE INDEX ix_simulation_runs_started ON pm.simulation_runs(started_at DESC);

CREATE TABLE pm.evaluation_reports (
    report_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generated_at  TIMESTAMPTZ NOT NULL,
    period_start  TIMESTAMPTZ NOT NULL,
    period_end    TIMESTAMPTZ NOT NULL,
    report        JSONB NOT NULL
);

CREATE INDEX ix_evaluation_reports_generated ON pm.evaluation_reports(generated_at DESC);

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
);

CREATE INDEX ix_simulation_validation_run ON pm.simulation_validation(run_id);
```

**`downgrade()` drops:**
- `pm.simulation_validation` first (has FK to simulation_runs)
- then `pm.evaluation_reports`
- then `pm.simulation_runs`

Use `op.execute(sa.text(...))` for raw SQL (same pattern as migration 003). Import `sqlalchemy as sa` and `alembic.op`.
