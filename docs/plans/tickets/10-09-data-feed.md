# Ticket: 10-09-data-feed

## Task
Implement the data feed module for aggregating Polymarket orderbook, Binance price, and computing derived metrics.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/data_feed.py`
- Create: `tests/unit/polymarket/test_data_feed.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 6.3)

### Optional read-only references
- `services/polymarket/adapters/clob_client.py`
- `services/polymarket/adapters/binance_client.py`

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 4
- Max total tool calls: 18

## Done criteria
- `data_feed.py` implements `DataFeed` class with methods:
  - `async def start(token_id: str) -> None` (subscribes to WebSocket, starts Binance polling)
  - `async def stop() -> None`
  - `def get_current_state() -> OrderbookState` (returns latest aggregated state)
  - `async def _on_book_update(book_data: dict) -> None` (WebSocket callback)
  - `async def _poll_binance() -> None` (every 5 seconds)
- `OrderbookState` includes: `best_bid`, `best_ask`, `midpoint`, `spread`, `bid_depth_1pct`, `ask_depth_1pct`, `imbalance`, `binance_price`, `timestamp`, `num_orders_at_best_bid`, `num_orders_at_best_ask`, `total_depth_top_3_levels`
- Computes queue position estimates: `our_bid_queue_ahead_size`, `our_ask_queue_ahead_size` (from full book depth)
- Computes reward eligibility: `is_within_reward_spread`, `is_above_min_size`
- Thread-safe state access (asyncio Lock)
- Unit tests cover: WebSocket update, Binance poll, state aggregation, staleness detection
- `docs/plans/PROGRESS.md` updated
