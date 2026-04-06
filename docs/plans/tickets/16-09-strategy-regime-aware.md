# Ticket: 16-09-strategy-regime-aware

## Task
Implement `poly_regime_v1` switching behavior by `RegimeState.primary_regime` and producing ABSTAIN/cancel semantics (AC-5).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- packages/strategies/poly_regime_v1.py
- packages/strategies/__init__.py
- tests/unit/strategies/test_poly_regime_v1.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md
- services/regime/schemas.py (RegimeState label set)

## Skill pack (optional, keep small)
- Required: `risk-manager`
- Optional: `quant-analyst`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `poly_regime_v1` behavior matches spec table:
  - R5 → emits ABSTAIN
  - R4 → emits cancel-all immediately
  - R3 → cancel-all + no new orders
- Unit test covers: regime switch R1→R3 triggers cancel-all within 1 tick (AC-5).
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-09 completion.

