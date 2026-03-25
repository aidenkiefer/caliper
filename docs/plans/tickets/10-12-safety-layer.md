# Ticket: 10-12-safety-layer

## Task
Implement the safety layer with pre-trade checks, circuit breakers, and emergency shutdown logic.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/safety.py`
- Create: `tests/unit/polymarket/test_safety.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 6.6)

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 3
- Max total tool calls: 15

## Done criteria
- `safety.py` implements `SafetyLayer` class with methods:
  - `def check_quote_safety(quote: QuoteDecision, session_state: dict) -> Tuple[bool, str]` (returns allowed, reason)
  - `def check_inventory_cap(inventory: Decimal, config: PolymarketConfig) -> bool`
  - `def check_session_loss_limit(session_pnl: Decimal, config: PolymarketConfig) -> bool`
  - `def check_binance_staleness(last_update: datetime) -> bool` (>30s = stale)
  - `def should_wind_down(time_to_close_minutes: int, config: PolymarketConfig) -> bool`
  - `async def emergency_shutdown(executor: Executor, reason: str) -> None` (cancel all, log, exit)
- Safety checks run before every quote placement
- If any check fails, quotes are not placed and reason is logged
- Emergency shutdown triggers on: session loss limit, heartbeat failure, critical error
- Unit tests cover: inventory cap, loss limit, staleness, wind-down timing, emergency shutdown
- `docs/plans/PROGRESS.md` updated
