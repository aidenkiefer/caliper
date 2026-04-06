# Ticket: 15-04-regime-quality-metrics

## Task
Implement `RegimeQualityReport` computation (entropy, switch rate, expected duration, agreement) and a deterministic `quality_score` composite (AC-3).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/regime/quality.py
- services/regime/schemas.py
- tests/unit/regime/test_quality_metrics.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- services/regime/classifiers/hmm.py (posterior + transition matrix access)

### Optional read-only references
- services/regime/classifiers/threshold.py (agreement metric needs threshold label)

### Agent type (optional)
- backend-agent

## Skill pack (optional, keep small)
- Required: `scikit-learn`
- Optional: `quant-analyst`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `posterior_entropy(p)` uses natural log; validates `entropy≈log(K)` for uniform posterior (AC-3).
- `switch_rate_per_hour` computed from a rolling window of primary-regime labels (define window size, default 1h).
- `expected_duration_minutes` computed from HMM transition matrix diagonal (document formula and edge-case handling).
- `agreement_with_threshold` implemented as Jaccard overlap on recent primary labels (document exact window).
- `quality_score` composite implemented deterministically and documented, with threshold `<0.5` meaning “fallback”.
- Unit tests cover:
  - uniform posterior entropy behavior
  - agreement trigger: `agreement_with_threshold < 0.5` forces fallback condition flag (AC-3)
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-04 completion.
