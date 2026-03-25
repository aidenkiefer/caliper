# Ticket: 10-07-fee-model

## Task
Implement the fee model for computing taker/maker fees and rebates based on Polymarket's fee curve.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/fee_model.py`
- Create: `tests/unit/polymarket/test_fee_model.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 6.9)
- `docs/research/microstructure-model.md` (section 1.1)

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 5
- Max grep/glob operations: 2
- Max total tool calls: 12

## Done criteria
- `fee_model.py` implements `FeeModel` class with methods:
  - `def compute_fee(price: Decimal, size: Decimal, is_maker: bool, fees_enabled: bool) -> Decimal`
  - `def compute_rebate(price: Decimal, size: Decimal) -> Decimal` (maker rebate only)
  - `def compute_net_pnl(gross_pnl: Decimal, fees_paid: Decimal, rebates_earned: Decimal) -> Decimal`
- Pre-March 30 logic: flat 2% taker fee, no maker fee, no rebates
- Post-March 30 logic: fee curve `f(p) = 0.02 × (1 - 2|p - 0.5|)`, maker rebate `r(p) = 0.01 × (1 - 2|p - 0.5|)`
- Unit tests cover: pre/post Mar 30, maker vs taker, edge cases (p=0.5, p=0.01, p=0.99)
- `docs/plans/PROGRESS.md` updated
