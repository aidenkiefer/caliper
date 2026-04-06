# Ticket: 15-07-performance-matrix-builder-and-store

## Task
Implement `PerformanceMatrix` builder + updater sourced from `pm.evaluation_reports`, including discounted `mu` and Ledoit–Wolf shrunk covariance (AC-4).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/allocation/performance_matrix.py
- services/allocation/schemas.py
- services/allocation/store.py (new; performance_matrices read/write)
- services/evaluation/schemas.py (read-only import)
- services/data/alembic/versions/006_create_regime_allocation_tables.py (only if this ticket includes migration; otherwise omit)
- tests/test_performance_matrix.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- services/evaluation/schemas.py (EvaluationReport/RegimeMetrics layout)

### Optional read-only references
- services/features/polymarket/store.py (asyncpg store pattern)

### Agent type (optional)
- backend-agent

## Skill pack (optional, keep small)
- Required: `risk-metrics-calculation`
- Optional: `scikit-learn` (Ledoit-Wolf)

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `PerformanceMatrixBuilder`:
  - Reads latest (or windowed) `pm.evaluation_reports.report` JSON and extracts per-strategy regime slices.
  - Computes:
    - discounted `mu` with half-life 7 days (`lambda = ln(2)/(7*24)` in hours; document units)
    - `sigma` per strategy per regime
    - shrunk covariance per regime using `sklearn.covariance.LedoitWolf`
- `PerformanceMatrixStore`:
  - `write_matrix(PerformanceMatrix)` inserts into `pm.performance_matrices`
  - `read_latest()` returns most recent matrix
- Unit tests (AC-4):
  - Known synthetic returns series -> discounted `mu` matches expected
  - Half-life check: weight at +7 days is 0.5 of today
  - Ledoit–Wolf output is PSD and well-conditioned (basic checks)
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-07 completion.

