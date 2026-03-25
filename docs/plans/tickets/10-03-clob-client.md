# Ticket: 10-03-clob-client

## Task
Implement the CLOB API client for order placement, cancellation, heartbeat, orderbook queries, and WebSocket market channel subscription.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/adapters/clob_client.py`
- Create: `tests/unit/polymarket/test_clob_client.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (sections 6.3, 6.5, 6.6)

### Optional read-only references
- Polymarket CLOB API docs: `https://docs.polymarket.com/api-reference/order/create-an-order`
- Polymarket WebSocket docs: `https://docs.polymarket.com/market-data/websocket/market-channel`
- `py-clob-client` SDK docs (if using the SDK directly)

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 4
- Max total tool calls: 18

## Done criteria
- `clob_client.py` implements `CLOBClient` class with methods:
  - `async def place_order(token_id, side, price, size, post_only=True) -> str` (returns order_id)
  - `async def cancel_order(order_id: str) -> bool`
  - `async def cancel_all() -> int` (returns count cancelled)
  - `async def send_heartbeat() -> dict` (returns heartbeat response with heartbeat_id)
  - `async def get_orderbook(token_id: str) -> dict` (bids, asks, timestamp)
  - `async def get_fee_rate(token_id: str) -> dict` (feesEnabled, rate)
  - `async def get_order_scoring(order_ids: List[str]) -> dict`
  - `async def subscribe_market_channel(token_id: str, callback: Callable) -> None` (WebSocket)
- All orders are EIP-712 signed using wallet private key (via `py-clob-client` SDK or `eth_account`)
- Handles HTTP 425 (engine restart) with exponential backoff
- Handles rate limits with adaptive pacing
- WebSocket reconnect logic on disconnect
- Unit tests cover: order placement, cancellation, heartbeat, book query, 425 handling, WebSocket message parsing
- `docs/plans/PROGRESS.md` updated
