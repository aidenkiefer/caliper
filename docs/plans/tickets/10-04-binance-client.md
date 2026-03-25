# Ticket: 10-04-binance-client

## Task
Implement the Binance API client for fetching 1H klines and current BTC price.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/adapters/binance_client.py`
- Create: `tests/unit/polymarket/test_binance_client.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 4.0, 6.3)

### Optional read-only references
- Binance API docs: `https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints`

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 5
- Max grep/glob operations: 3
- Max total tool calls: 12

## Done criteria
- `binance_client.py` implements `BinanceClient` class with methods:
  - `async def get_1h_candle(symbol: str, timestamp: datetime) -> dict` (returns OHLCV for specific hour)
  - `async def get_current_price(symbol: str) -> Decimal` (latest price from 1m kline)
  - `async def get_1h_candles_range(symbol: str, start: datetime, end: datetime) -> List[dict]`
- Returns dict with keys: `open_time`, `open`, `high`, `low`, `close`, `volume`, `close_time`
- Handles rate limits and network errors with retries
- Unit tests cover: successful fetch, candle not available yet, API error, timestamp alignment
- `docs/plans/PROGRESS.md` updated
