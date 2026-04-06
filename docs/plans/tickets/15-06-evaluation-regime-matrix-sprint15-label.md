# Ticket: 15-06-evaluation-regime-matrix-sprint15-label

## Task
Extend Sprint 13 evaluation regime slicing to include Sprint 15 semantic regime label `primary_regime` (R1–R5) so `pm.evaluation_reports` can feed the PerformanceMatrix builder.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/evaluation/regime_matrix.py
- services/evaluation/schemas.py (only if needed for regime label naming; prefer not)
- services/regime/classifiers/threshold.py (read-only import usage OK; avoid circular deps)
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- services/evaluation/regime_matrix.py (current dimensions)

### Optional read-only references
- packages/common/polymarket_schemas.py (FeatureSnapshot inputs for threshold classifier)

### Agent type (optional)
- backend-agent

## Skill pack (optional, keep small)
- Required: `quant-analyst`
- Optional: `risk-manager`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `services/evaluation/regime_matrix.py` adds a new derived regime dimension:
  - `primary_regime` computed using `ThresholdRegimeClassifier` on each FeatureSnapshot (connectivity inputs set to “healthy defaults” for offline evaluation unless explicit metrics exist).
- `compute_regime_metrics` emits additional `RegimeMetrics` entries like `primary_regime=R1`, `primary_regime=R2`, etc.
- Behavior is deterministic and does not introduce import cycles (document any needed helper types).
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-06 completion.

