# Ticket: 15-10-allocation-engine-service-and-store

## Task
Implement `AllocationEngine` allocation loop, persistence to `pm.allocation_decisions`, and “current decision” in-memory cache (AC-8/9 subset).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/allocation/engine.py
- services/allocation/store.py
- services/allocation/schemas.py
- services/allocation/risk_layer.py
- services/allocation/methods/**
- tests/test_allocation_engine_loop.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- services/portfolio/allocator.py (CapitalBudget schema)

### Optional read-only references
- services/ml/probability_model/predictor.py (async loop + signal bus pattern)

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
- `AllocationEngine`:
  - consumes `RegimeState` (from queue or direct call) + latest `PerformanceMatrix`
  - produces `AllocationDecision` with:
    - `weights`, `method_used`, `confidence` (derived from regime quality)
    - `hard_constraints_applied` list populated correctly
    - embeds `CapitalBudget` (from `services/portfolio/allocator.py`)
  - publishes to optional output_queue (signal bus)
  - writes decisions to DB asynchronously (non-blocking)
- `AllocationStore`:
  - `write_decision(AllocationDecision)` to `pm.allocation_decisions`
  - `read_latest()` and `read_window(start,end)` for API
- Integration-style test: run `AllocationEngine` for 10 ticks on synthetic regime states; verify constraints are always satisfied (AC-10 intent).
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-10 completion.

