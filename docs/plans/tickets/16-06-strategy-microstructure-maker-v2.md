# Ticket: 16-06-strategy-microstructure-maker-v2

## Task
Implement `poly_mm_v2` as an improved Polymarket microstructure market maker strategy (Strategy 1).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- packages/strategies/poly_mm_v2.py
- packages/strategies/__init__.py
- packages/strategies/base.py (ONLY if required for shared interfaces)
- tests/unit/strategies/test_poly_mm_v2.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md
- packages/strategies/polymarket_mm_strategy.py (existing baseline)

### Optional read-only references
- services/regime/schemas.py (RegimeState)

## Skill pack (optional, keep small)
- Required: `quant-analyst`
- Optional: `risk-manager`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `poly_mm_v2`:
  - inventory skew logic `c_t = m_t - φ*q_t`
  - spread widening ×2 in last 10 minutes
  - reward-aware sizing metadata (deterministic rule; no external calls)
  - suppress quoting in `RegimeState.primary_regime == "R3"`
- Emits `UnifiedSignal(signal_type=MARKET_MAKING)` with required metadata keys.
- Unit test asserts inventory skew + near-close widening behavior using synthetic inputs.
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-06 completion.

