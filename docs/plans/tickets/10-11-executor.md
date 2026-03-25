# Ticket: 10-11-executor

## Task
Implement the executor module for order placement, cancellation, heartbeat management, and fill tracking.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/executor.py`
- Create: `tests/unit/polymarket/test_executor.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 6.5)

### Optional read-only references
- `services/polymarket/adapters/clob_client.py`
- `services/polymarket/wallet.py`

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 4
- Max total tool calls: 18

## Done criteria
- `executor.py` implements `Executor` class with methods:
  - `async def place_quotes(quote: QuoteDecision, token_id: str, quote_version: int) -> Tuple[str, str]` (returns bid_order_id, ask_order_id)
  - `async def cancel_all_orders() -> int` (returns count cancelled)
  - `async def start_heartbeat() -> None` (starts background task sending heartbeat every 10s)
  - `async def stop_heartbeat() -> None`
  - `async def handle_fill(fill_data: dict) -> None` (callback from WebSocket)
- Enforces `post_only=True` on all orders
- Tracks `quote_version_id` and `time_on_book_seconds` for each order
- Heartbeat runs in background asyncio task, logs failures but does not crash
- Fill handler updates inventory and notifies recorder
- Unit tests cover: order placement, cancellation, heartbeat loop, fill handling, post-only enforcement
- `docs/plans/PROGRESS.md` updated
