# Ticket: 15-09-allocation-risk-layer-and-blending

## Task
Implement allocation blending + hard/soft constraint enforcement (AC-7/8) in `risk_layer.py`.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/allocation/risk_layer.py
- services/allocation/schemas.py
- tests/test_allocation_risk_layer.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md

### Optional read-only references
- docs/risk-policy.md (kill-switch mindset; allocation must default to safe)

### Agent type (optional)
- backend-agent

## Skill pack (optional, keep small)
- Required: `risk-manager`
- Optional: `quant-analyst`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- Blending:
  - `alpha = clamp(1 - entropy/log(K), 0, 1)` where K is count of HMM regimes
  - uniform posterior -> alpha=0 -> pure risk-parity baseline (AC-8)
  - near-certain posterior -> alpha->1 -> advanced method weights dominate
- Hard constraints (AC-7):
  - R4: all weights -> 0
  - per-strategy cap 0.40
  - portfolio kill switch input `portfolio_drawdown >= 0.15` -> all weights 0
  - per-strategy drawdown `>= 0.20` -> that strategy weight 0
  - capital velocity cap: per-cycle weight increase <= 0.10 (document exact implementation)
  - R3: set all MM strategy weights -> 0 (MM strategies provided explicitly via `mm_strategy_ids`)
- Soft constraints:
  - volatility targeting: scale weights down if portfolio realized vol exceeds `target_vol = 0.10` (annualized)
  - turnover penalty: penalize large weight changes via smoothing (document exact rule)
- Unit tests cover each hard constraint path explicitly.
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-09 completion.

