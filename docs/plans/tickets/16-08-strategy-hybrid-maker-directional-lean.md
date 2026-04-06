# Ticket: 16-08-strategy-hybrid-maker-directional-lean

## Task
Implement `poly_hybrid_v1` combining maker quoting with a directional lean; it must never take liquidity (AC-4).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- packages/strategies/poly_hybrid_v1.py
- packages/strategies/__init__.py
- tests/unit/strategies/test_poly_hybrid_v1.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md
- packages/strategies/poly_mm_v2.py
- packages/strategies/poly_directional_v1.py

## Skill pack (optional, keep small)
- Required: `quant-analyst`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- When directional trigger fires:
  - tightens favorable side and widens/cancels unfavorable side (verifiable in metadata) (AC-4)
  - emits only maker-style `UnifiedSignal` (no taker/cross-spread intent)
- Unit tests cover AC-4 behavior with synthetic `M(t)` inputs.
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-08 completion.

