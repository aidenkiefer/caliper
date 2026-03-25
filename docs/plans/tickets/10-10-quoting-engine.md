# Ticket: 10-10-quoting-engine

## Task
Implement the quoting engine for V1 fixed-spread symmetric market making.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/quoting_engine.py`
- Create: `tests/unit/polymarket/test_quoting_engine.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 6.4)

### Optional read-only references
- `services/polymarket/data_feed.py`
- `services/polymarket/config.py`

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 7
- Max grep/glob operations: 3
- Max total tool calls: 15

## Done criteria
- `quoting_engine.py` implements `QuotingEngine` class with methods:
  - `def compute_quotes(orderbook_state: OrderbookState, inventory: Decimal, config: PolymarketConfig) -> QuoteDecision`
- `QuoteDecision` includes: `bid_price`, `ask_price`, `bid_size`, `ask_size`, `should_quote: bool`, `reason: str`
- V1 logic: `bid = mid - spread`, `ask = mid + spread` (symmetric, no inventory skew)
- Respects tick size (rounds to nearest 0.01)
- Returns `should_quote=False` if: midpoint is stale, spread is too wide (>10 cents), inventory cap reached
- Unit tests cover: normal quoting, inventory cap, stale data, wide spread, tick size rounding
- `docs/plans/PROGRESS.md` updated
