# Ticket: 16-10-fleet-orchestrator

## Task
Implement `FleetOrchestrator` end-to-end paper-mode event loop: subscribe to ranker/regime/allocation/predictor outputs, generate strategy signals, allocate budget, run risk checks, and dispatch to adapter/simulation (AC-6/7).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/fleet/**
- services/portfolio/allocator.py (ONLY for wiring / types if needed)
- services/risk/manager.py (read-only import use OK; avoid behavior change)
- services/polymarket/executor.py (ONLY if needed to add paper/dry-run hook; keep minimal)
- tests/integration/fleet/test_fleet_orchestrator_paper_mode.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md
- services/portfolio/allocator.py
- services/polymarket/session.py (existing orchestration patterns)

### Optional read-only references
- services/ml/probability_model/predictor.py (signal bus pattern)
- services/simulation/runner.py (paper fill generation)

## Skill pack (optional, keep small)
- Required: `async-python-patterns`
- Optional: `risk-manager`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `services/fleet/registry.py` loads the 4 Sprint-16 strategies by ID.
- `services/fleet/orchestrator.py` processes:
  - `FeatureSnapshot`, `RankedUniverse`, `AllocationDecision`, `RegimeState`, `PredictionRecord`
  - emits paper-mode orders only (no live submissions)
- Integration test runs 5 synthetic ticks and verifies paper fills are recorded (AC-10 integration intent).
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-10 completion.

