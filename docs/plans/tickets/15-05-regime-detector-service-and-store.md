# Ticket: 15-05-regime-detector-service-and-store

## Task
Implement `RegimeDetector` real-time inference loop + asyncpg persistence to `pm.regime_states` (AC-1/3 + DB table write).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/regime/detector.py
- services/regime/classifiers/threshold.py
- services/regime/classifiers/hmm.py
- services/regime/quality.py
- services/regime/schemas.py
- services/regime/store.py (new)
- services/data/alembic/versions/006_create_regime_allocation_tables.py (write table only if this ticket includes migration; otherwise omit)
- tests/unit/regime/test_detector_loop.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- services/features/polymarket/store.py (asyncpg store pattern)

### Optional read-only references
- services/ml/probability_model/predictor.py (async loop + optional output_queue “signal bus” pattern)

### Agent type (optional)
- backend-agent

## Skill pack (optional, keep small)
- Required: `async-python-patterns`
- Optional: `risk-manager`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `RegimeDetector`:
  - Runs every 30 seconds (configurable) consuming `FeatureSnapshot` inputs.
  - Computes threshold regime (R4/R5 first, then remaining) and HMM posterior.
  - Computes `RegimeQualityReport` each tick.
  - Blends source selection:
    - if `quality_score < 0.5` -> emit `source="threshold"` + one-hot probs
    - else -> emit `source="hmm"` or `source="blended"` with soft probs over R1–R3 (and respecting R4/R5 overrides)
  - Implements minimum-hold filter: require 3 consecutive ticks before switching `primary_regime`.
- `RegimeStore`:
  - Asyncpg pool lifecycle
  - `write_state(RegimeState)` inserts into `pm.regime_states`
  - `read_latest(market_id?)` and `read_window(start,end,market_id?)` for API needs
- Loop DB writes are non-blocking (fire-and-forget task); failures logged, do not crash loop.
- Test covers: 10 synthetic ticks -> never violates precedence rules; minimum-hold behavior works.
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-05 completion.
