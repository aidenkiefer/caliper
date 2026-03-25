# Ticket: 10-13-recorder

## Task
Implement the recorder module for writing all session data to TimescaleDB.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/recorder.py`
- Create: `tests/unit/polymarket/test_recorder.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 6.7, section 3)

### Optional read-only references
- `services/data/` (example DB connection patterns)

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 4
- Max total tool calls: 18

## Done criteria
- `recorder.py` implements `Recorder` class with methods:
  - `async def create_session(market: MarketInfo, config: PolymarketConfig) -> UUID`
  - `async def record_order(order_data: dict, session_id: UUID) -> None`
  - `async def record_fill(fill_data: dict, session_id: UUID) -> None`
  - `async def record_snapshot(snapshot: OrderbookState, session_id: UUID) -> None`
  - `async def record_pnl_snapshot(pnl_data: dict, session_id: UUID) -> None`
  - `async def record_binance_candle(candle: dict, session_id: UUID) -> None`
  - `async def finalize_session(session_id: UUID, final_state: dict) -> None`
  - `async def compute_toxic_flow_by_minute(session_id: UUID) -> None`
  - `async def update_adverse_selection_async(fill_id: UUID, midpoint_5s: Decimal, midpoint_10s: Decimal) -> None`
- Uses asyncpg connection pool for writes
- Batch inserts for snapshots (buffer 10 rows, flush every 30s or on buffer full)
- Immediate inserts for orders and fills
- Computes session regime tags at finalization: `volatility_regime`, `spread_regime`, `volume_regime`, `btc_trend_regime`
- Unit tests use mock DB and cover: session creation, order/fill recording, snapshot batching, regime computation
- `docs/plans/PROGRESS.md` updated
