# Ticket: 15-11-db-migration-regime-allocation-tables

## Task
Add Alembic migration creating Sprint 15 `pm.regime_states`, `pm.allocation_decisions`, `pm.performance_matrices` tables (and hypertables where specified).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/data/alembic/versions/006_create_regime_allocation_tables.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- services/data/alembic/versions/005_create_probability_model_tables.py (migration style)

### Optional read-only references
- docs/data-contracts.md (schema conventions)

### Agent type (optional)
- data-agent

## Skill pack (optional, keep small)
- Required: `postgres-best-practices`
- Optional: `database-design`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- Migration creates:
  - `pm.regime_states` + hypertable on `detected_at`
  - `pm.allocation_decisions` + hypertable on `decided_at`
  - `pm.performance_matrices` (no hypertable per spec)
- Appropriate indexes added for “latest” queries (e.g., `(detected_at DESC)` / `(decided_at DESC)`).
- Downgrade drops tables in safe reverse dependency order.
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-11 completion.

