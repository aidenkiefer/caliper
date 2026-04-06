# Ticket: 15-13-tests-regime-and-allocation

## Task
Add full unit + integration test coverage required by Sprint 15 acceptance criteria (AC-1..AC-10).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- tests/unit/regime/test_threshold_classifier.py
- tests/unit/regime/test_hmm_classifier.py
- tests/unit/regime/test_quality_metrics.py
- tests/unit/regime/test_detector_loop.py
- tests/unit/allocation/test_performance_matrix.py
- tests/unit/allocation/test_allocation_methods.py
- tests/unit/allocation/test_risk_layer.py
- tests/unit/allocation/test_allocation_engine_unit.py
- tests/integration/allocation/test_allocation_engine_loop.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md

### Optional read-only references
- existing test patterns under `services/api/test_*.py`

### Agent type (optional)
- qa-agent

## Skill pack (optional, keep small)
- Required: `python-testing-patterns`
- Optional: `testing-patterns`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- Unit tests implemented for:
  - Threshold classifier (all 5 regimes) (AC-1)
  - HMM classifier (synthetic train; posterior sums to 1) (AC-2)
  - Quality metrics (entropy + agreement fallback) (AC-3)
  - PerformanceMatrix (discounted mu + Ledoit–Wolf) (AC-4)
  - risk_parity / hrp / bounded_kelly (AC-5/6)
  - Hard constraints enforcement (AC-7)
- Integration test:
  - run `AllocationEngine` for 10 ticks on synthetic regime states; verify constraints always satisfied (AC-10)
- No test-running required in this repo workflow; tests are added but not executed unless the user explicitly asks.
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-13 completion.
