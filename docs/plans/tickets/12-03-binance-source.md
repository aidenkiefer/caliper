# Ticket: 12-03-binance-source

## Task
Implement `services/features/polymarket/sources/binance.py`: an async Binance data source that polls 1-minute spot klines and perpetual futures premium index, maintaining rolling buffers for volatility and momentum calculations.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/features/polymarket/sources/binance.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-12-feature-layer-spec.md` (sections: Feature Family 3 — Probabilistic, Data Sources table)
- `docs/research/probabilities.md` (sections: Price-path features from Binance, Perp funding/basis proxies)

### Optional read-only references
- `services/polymarket/clients/binance_client.py` (existing Binance client — read for reference; do NOT import directly)

## Agent type
backend-agent

## Skill pack
- `async-python-patterns` (async polling, rolling buffers)

## Context + tool budget
- Max file reads: 5
- Max grep/glob operations: 3
- Max total tool calls: 10

## Done criteria

**`BinanceSource` class in `sources/binance.py`:**
- `async def start() -> None` — launches two background polling tasks: klines every 60s, premium index every 30s
- `async def stop() -> None` — cancels polling tasks gracefully
- Rolling buffer stores the last 60 one-minute klines (as `KlineBar` named-tuples: `open_time`, `open`, `high`, `low`, `close`, `volume`)
- `get_hour_open() -> Decimal` — returns the open price of the current 1h BTC candle (first 1m kline open of the current hour)
- `get_btc_price() -> Decimal` — returns the close of the most recent 1m kline
- `get_kline_buffer() -> List[KlineBar]` — returns current rolling buffer (up to 60 bars); raises `DataUnavailable` if buffer empty
- `get_premium_index() -> PremiumIndex` — returns latest `PremiumIndex(mark_price, index_price, last_funding_rate, next_funding_time, received_at)`
- `source_timestamp: datetime` updated each time any poll completes
- Polling uses `httpx.AsyncClient` with 10s timeout; retries up to 3 times with 2s backoff on failure; logs WARNING on retry
- Endpoints used:
  - `GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=60`
  - `GET https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT`

**`KlineBar` named-tuple** and **`PremiumIndex` dataclass** defined in the same file

**`DataUnavailable` exception** defined in `sources/__init__.py` (shared across CLOB and Binance)

**`sources/__init__.py`** updated to export `BinanceSource`, `KlineBar`, `PremiumIndex`, `DataUnavailable`

**`docs/plans/PROGRESS.md`** updated
