# Ticket: 12-05-db-migration

## Task
Add an Alembic migration that creates the `pm.features` TimescaleDB hypertable with JSONB feature storage and appropriate indexes.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/data/alembic/versions/XXXX_pm_features_hypertable.py` (Alembic will generate the prefix; use a descriptive name like `create_pm_features_hypertable`)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-12-feature-layer-spec.md` (section: Database Migration)

### Optional read-only references
- `services/data/alembic/versions/` (any existing `pm.*` migration for patterns — read-only)
- `services/data/alembic/env.py` (schema handling patterns)

## Agent type
backend-agent

## Skill pack
None required (SQL migration)

## Context + tool budget
- Max file reads: 4
- Max grep/glob operations: 3
- Max total tool calls: 8

## Done criteria

**Alembic migration file:**
- `upgrade()` creates the `pm.features` table with exactly these columns:
  ```sql
  id            UUID DEFAULT gen_random_uuid() NOT NULL,
  market_id     TEXT NOT NULL,
  token_id      TEXT NOT NULL,
  captured_at   TIMESTAMPTZ NOT NULL,
  features      JSONB NOT NULL,
  PRIMARY KEY (id, captured_at)
  ```
- Calls `SELECT create_hypertable('pm.features', 'captured_at')` via `op.execute()`
- Creates index: `CREATE INDEX ON pm.features (market_id, captured_at DESC)`
- `downgrade()` drops the index, then the table (`DROP TABLE IF EXISTS pm.features`)
- Migration uses `schema='pm'` for the table creation (consistent with existing `pm.*` tables)
- No Python imports of application code — uses only `sqlalchemy` and `alembic.op`

**`docs/plans/PROGRESS.md`** updated
