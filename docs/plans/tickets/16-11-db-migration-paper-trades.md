# Ticket: 16-11-db-migration-paper-trades

## Task
Add Alembic migration + asyncpg store for `pm.paper_trades` and wire non-blocking writes from the fleet orchestrator (AC-6/7).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/data/alembic/versions/007_create_pm_paper_trades_table.py
- services/fleet/paper_store.py
- services/fleet/schemas.py
- tests/integration/fleet/test_paper_trade_store.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md
- services/data/alembic/versions/006_create_regime_allocation_tables.py (migration style)

## Skill pack (optional, keep small)
- Required: `postgres-best-practices`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- Migration creates `pm.paper_trades` with:
  - timestamp column for hypertable (if Timescale is used in repo; mirror prior patterns)
  - indexes for “latest” / “by strategy” / “by market” queries
- `PaperTradeStore.write_fill(...)` performs async insert using asyncpg pool.
- Tests validate the SQL payload shape using a fake pool or lightweight stub (no DB required).
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-11 completion.

