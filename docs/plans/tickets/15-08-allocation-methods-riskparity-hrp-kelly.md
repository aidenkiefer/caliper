# Ticket: 15-08-allocation-methods-riskparity-hrp-kelly

## Task
Implement allocation methods: risk parity baseline, HRP, and bounded Kelly (AC-5/6), as pure functions with deterministic outputs.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/allocation/methods/risk_parity.py
- services/allocation/methods/hrp.py
- services/allocation/methods/kelly.py
- services/allocation/schemas.py
- tests/test_allocation_methods.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- services/allocation/schemas.py (PerformanceMatrix fields)

### Optional read-only references
- docs/research/regime-allocation.md

### Agent type (optional)
- backend-agent

## Skill pack (optional, keep small)
- Required: `risk-metrics-calculation`
- Optional: `scikit-learn`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `risk_parity_weights(sigma_by_strategy, cap, cash_buffer_min)`:
  - weights proportional to 1/sigma
  - sums to <= 1 with residual as cash (AC-5)
- `hrp_weights(cov_matrix, strategies)`:
  - hierarchical clustering + recursive bisection
  - deterministic (seeded / stable sorting) (AC-6)
- `bounded_kelly_weights(mu, cov, max_weight=0.40, total_leverage_cap=1.0)`:
  - solves Kelly fraction in a stable way (document approach)
  - clamps and renormalizes respecting caps
- Unit tests:
  - risk parity proportionality
  - HRP “more balanced than equal-weight on concentrated covariance” (define exact numeric check)
  - Kelly bounds respected
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-08 completion.

