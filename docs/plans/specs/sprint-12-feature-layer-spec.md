# Sprint 12: Feature Layer Unification

**Version:** v2.2.0  
**Status:** Spec  
**Research sources:** `docs/research/microstructure-model.md`, `docs/research/probabilities.md`, `docs/research/regime-allocation.md`  
**Skills to load:** `quant-analyst`, `data-engineering-data-pipeline`, `async-python-patterns`, `backend-dev-guidelines`

---

## Overview

The current feature pipeline (`services/features/`) was built for equity strategies and produces a fixed set of technical indicators (SMA, RSI, etc.) for price bars. It has no awareness of Polymarket's CLOB microstructure, binary settlement mechanics, or regime state.

Sprint 12 unifies the feature layer into a **multi-dimensional, market-type-aware feature pipeline** that feeds all downstream models (probability model, regime detector, cross-sectional ranker, fleet strategies). Every feature must be computable in real time and reproducible offline for backtesting.

This sprint builds the **data foundation** for v2.3–v2.7. No model training happens here — only feature engineering, storage, and serving.

---

## Goals

1. Define and implement four unified feature families with clear schemas.
2. Build an async, real-time feature builder for Polymarket CLOB + Binance klines.
3. Extend the existing `services/features/` pipeline with a `FeatureStore` interface for reading/writing feature snapshots.
4. Expose features via a lightweight API endpoint for dashboards and downstream models.
5. All features must be reproducible from historical data (for use in backtesting and model training).

---

## Feature Families

### Family 1 — Market State

Features derived from the current order book snapshot and settlement mechanics. Source: Polymarket CLOB WebSocket (`book`, `price_change`, `last_trade_price`).

| Feature | Description | Formula |
|---------|-------------|---------|
| `mid_price` | Best bid/ask midpoint | `(best_bid + best_ask) / 2` |
| `implied_probability` | Displayed probability (midpoint if spread ≤ $0.10, else last trade) | See microstructure-model.md §State variables |
| `spread` | Best ask minus best bid | `best_ask - best_bid` |
| `spread_bps` | Spread as basis points of midpoint | `spread / mid_price * 10000` |
| `time_to_close_seconds` | Seconds until market resolution | `market_close_ts - now_ts` |
| `time_since_open_seconds` | Seconds since market opened | `now_ts - market_open_ts` |
| `book_depth_bid_5tick` | Total bid size within 5 ticks of best bid | Sum over bid levels |
| `book_depth_ask_5tick` | Total ask size within 5 ticks of best ask | Sum over ask levels |
| `time_since_last_trade` | Seconds since last executed trade | From `last_trade_price` event |
| `time_since_last_price_change` | Seconds since last book update | From `price_change` event |

### Family 2 — Microstructure

Features capturing order flow dynamics, adverse selection risk, and maker execution quality. Sources: Polymarket CLOB WebSocket + Data API trades.

| Feature | Description | Notes |
|---------|-------------|-------|
| `order_book_imbalance` | Bid depth minus ask depth normalized | `(depth_bid - depth_ask) / (depth_bid + depth_ask)` over top-of-book |
| `trade_flow_imbalance_1m` | Buy volume minus sell volume over last 1 min | From Data API `/trades`; positive = net buying |
| `trade_flow_imbalance_5m` | Same over last 5 min | Rolling window |
| `last_5min_volume_share` | Fraction of window volume in last 5 minutes | Toxicity proxy for near-close adverse selection |
| `aggressor_buy_fraction_1m` | Fraction of recent trades that are buys | From trade side classification |
| `fill_rate_proxy` | Estimated fill probability for post-only at mid±1tick | Based on queue depth and recent trade intensity |
| `vpin_proxy` | Volume-weighted imbalance as adverse selection proxy | Simplified VPIN: `|buy_vol - sell_vol| / total_vol` over rolling bucket |
| `fee_rate_current` | Current taker fee rate for this token | From CLOB `/fee-rate?token_id=...` |
| `reward_eligible` | Whether this market qualifies for liquidity rewards | From CLOB rewards endpoint; boolean |
| `reward_max_spread` | Max allowed spread to qualify for rewards | From CLOB rewards config |
| `reward_min_size` | Min size to qualify for rewards | From CLOB rewards config |
| `maker_rebate_pct` | Current maker rebate percentage | From docs; 20% for crypto |

### Family 3 — Probabilistic

Features encoding the relationship between market price and external price information. Sources: Binance spot klines + Binance USDⓈ-M futures.

| Feature | Description | Notes |
|---------|-------------|-------|
| `btc_distance_to_open` | ln(BTC_price_now / BTC_open) for this hour | Key predictor for P(close ≥ open) |
| `btc_rv_1m` | Realized BTC volatility over last 1 minute | Sum of squared log-returns from 1m klines |
| `btc_rv_5m` | Realized BTC volatility over last 5 minutes | Rolling window |
| `btc_rv_15m` | Realized BTC volatility over last 15 minutes | Rolling window |
| `btc_momentum_5m` | BTC return over last 5 minutes | Simple log return |
| `btc_sign_persistence_5m` | Fraction of 1m returns that are positive over last 5m | Trend proxy |
| `btc_funding_rate` | Latest perpetual funding rate | From Binance USDⓈ-M `/fapi/v1/premiumIndex` |
| `btc_basis_proxy` | Mark price minus index price (scaled) | From futures `premiumIndex` |
| `implied_vs_btc_fair` | Polymarket implied probability minus BTC-path-derived fair probability | `implied_probability - btc_fair_prob`; requires fair prob model |
| `mispricing` | Same as above, but computed from trained model | Available after Sprint 14 trains the probability model |

*Note:* `btc_fair_prob` is a placeholder set to `0.5 + btc_distance_to_open * calibration_factor` until Sprint 14 provides a trained model.

### Family 4 — Regime

Features encoding market-wide and local market conditions. Sources: same as Families 1–3 plus rolling aggregations.

| Feature | Description | Notes |
|---------|-------------|-------|
| `vol_regime` | Discretized volatility bucket (low/medium/high) | Based on `btc_rv_1h` vs historical thresholds |
| `trend_regime` | Trending vs mean-reverting label | Based on `btc_sign_persistence_5m` and slope over 30m |
| `time_bucket` | Hour-of-day bucket (early/mid/late) | Encodes intraday liquidity patterns |
| `near_close_flag` | Boolean; True if within 10 minutes of market close | Hard threshold |
| `toxicity_regime` | Low/medium/high adverse selection risk | Based on `vpin_proxy` and `last_5min_volume_share` |
| `spread_regime` | Tight/wide relative to market history | `spread` vs rolling 24h median spread |
| `liquidity_score` | Composite of depth, spread, and activity | `depth_5tick / (spread * btc_rv_5m + ε)`; normalized |
| `competitive_pressure` | Market tightness indicator | Inverse of `spread_bps`; proxy for maker competition |
| `hour_volume_percentile` | Historical volume percentile for this hour-of-day | From `pm.*` trade history |

---

## Architecture

### New: `services/features/polymarket/`

```
services/features/
├── __init__.py
├── pipeline.py           # existing equity pipeline (untouched)
├── polymarket/
│   ├── __init__.py
│   ├── builder.py        # FeatureBuilder: computes all 4 families per tick
│   ├── store.py          # FeatureStore: read/write snapshots to TimescaleDB
│   ├── schemas.py        # Pydantic schemas: FeatureSnapshot, FeatureRecord
│   └── sources/
│       ├── __init__.py
│       ├── clob.py       # CLOB WebSocket + REST data ingestion
│       └── binance.py    # Binance klines + futures data ingestion
```

### `FeatureSnapshot` Schema (Pydantic)

```python
class FeatureSnapshot(BaseModel):
    market_id: str                    # condition_id
    token_id: str                     # YES token_id
    captured_at: datetime             # UTC timestamp of snapshot
    time_to_close_seconds: float
    # Family 1
    mid_price: Decimal
    implied_probability: Decimal
    spread: Decimal
    spread_bps: Decimal
    book_depth_bid_5tick: Decimal
    book_depth_ask_5tick: Decimal
    time_since_last_trade: float
    # Family 2
    order_book_imbalance: Decimal
    trade_flow_imbalance_1m: Decimal
    trade_flow_imbalance_5m: Decimal
    last_5min_volume_share: Decimal
    vpin_proxy: Decimal
    fee_rate_current: Decimal
    reward_eligible: bool
    reward_max_spread: Optional[Decimal]
    reward_min_size: Optional[Decimal]
    # Family 3
    btc_distance_to_open: Decimal
    btc_rv_1m: Decimal
    btc_rv_5m: Decimal
    btc_rv_15m: Decimal
    btc_momentum_5m: Decimal
    btc_sign_persistence_5m: Decimal
    btc_funding_rate: Decimal
    btc_basis_proxy: Decimal
    # Family 4
    vol_regime: Literal["low", "medium", "high"]
    trend_regime: Literal["trending", "mean_reverting", "neutral"]
    time_bucket: Literal["early", "mid", "late"]
    near_close_flag: bool
    toxicity_regime: Literal["low", "medium", "high"]
    spread_regime: Literal["tight", "normal", "wide"]
    liquidity_score: Decimal
    competitive_pressure: Decimal
```

### `FeatureStore`

Writes `FeatureSnapshot` records to a new `pm.features` TimescaleDB hypertable (partitioned by `captured_at`). Provides:

- `write(snapshot: FeatureSnapshot) -> None`
- `read_window(market_id, start, end) -> List[FeatureSnapshot]`
- `read_latest(market_id) -> Optional[FeatureSnapshot]`

### `FeatureBuilder`

An async class that runs on a configurable tick cadence (default: 5 seconds). On each tick:

1. Pull latest orderbook state from CLOB WebSocket buffer.
2. Pull latest Binance kline data from Binance buffer.
3. Compute all feature families.
4. Write snapshot to `FeatureStore`.
5. Publish to an in-memory `asyncio.Queue` for downstream consumers (probability model, strategy).

### Integration with `PolymarketMMStrategy`

The `FeatureBuilder` output queue replaces the raw `OrderbookState` currently passed to `on_market_data()`. The strategy's `on_market_data` signature is updated to accept `FeatureSnapshot` (or both, via optional typing).

---

## Database Migration

Add a new Alembic migration in `services/data/alembic/versions/` creating:

```sql
CREATE TABLE pm.features (
    id            UUID DEFAULT gen_random_uuid() NOT NULL,
    market_id     TEXT NOT NULL,
    token_id      TEXT NOT NULL,
    captured_at   TIMESTAMPTZ NOT NULL,
    features      JSONB NOT NULL,           -- serialized FeatureSnapshot fields
    PRIMARY KEY (id, captured_at)
);

SELECT create_hypertable('pm.features', 'captured_at');
CREATE INDEX ON pm.features (market_id, captured_at DESC);
```

The `features` column stores the full `FeatureSnapshot` as JSONB for flexibility. Typed columns for the highest-frequency read fields (`market_id`, `token_id`, `captured_at`) are indexed separately.

---

## API Endpoint

Add a new router `services/api/routers/features.py`:

- `GET /v1/features/{market_id}/latest` → returns `FeatureSnapshot`
- `GET /v1/features/{market_id}/history?start=&end=&limit=` → returns `List[FeatureSnapshot]`

---

## Data Sources

| Source | Endpoint | Cadence | Used for |
|--------|----------|---------|---------|
| Polymarket CLOB WebSocket | `wss://ws-subscriptions-clob.polymarket.com/ws/market` | Real-time | Orderbook, trades, price changes |
| Polymarket CLOB REST | `GET /book?token_id=...` | On startup / reconnect | Orderbook snapshot for state recovery |
| Polymarket CLOB REST | `GET /fee-rate?token_id=...` | Once per market | Taker fee rate |
| Polymarket CLOB Rewards | Rewards endpoints | Daily | Reward eligibility, max spread, min size |
| Polymarket Data API | `GET /trades?market=...` | Polling, 10s | Trade tape for flow imbalance |
| Binance Spot REST | `GET /api/v3/klines?symbol=BTCUSDT&interval=1m` | Polling, 60s | 1m candles for RV, momentum |
| Binance Futures REST | `GET /fapi/v1/premiumIndex` | Polling, 30s | Funding rate, mark/index price |

---

## Acceptance Criteria

### AC-1: Feature computation
- All 4 feature families compute without error for a live Polymarket BTC hourly market.
- `FeatureSnapshot` is validated by Pydantic with no missing required fields.

### AC-2: Real-time latency
- `FeatureBuilder` produces a new `FeatureSnapshot` every ≤ 5 seconds.
- Total compute time per snapshot (excluding network I/O) is ≤ 100ms.

### AC-3: Persistence
- `FeatureStore.write()` writes a snapshot to `pm.features` and `read_latest()` returns it correctly.
- Historical snapshots are queryable by `market_id` and time range.

### AC-4: Regime features
- `vol_regime`, `trend_regime`, `toxicity_regime`, `spread_regime`, and `near_close_flag` all produce correct discrete labels for a set of test input vectors.

### AC-5: Reproducibility
- Given the same historical orderbook and trade data as input, `FeatureBuilder` produces identical `FeatureSnapshot` output deterministically.
- Offline (backtest) mode and online (live) mode share the same computation path.

### AC-6: API endpoint
- `GET /v1/features/{market_id}/latest` returns a valid JSON representation of `FeatureSnapshot`.
- `GET /v1/features/{market_id}/history` returns an ordered list with correct time bounds.

### AC-7: Tests
- Unit tests cover every feature formula with explicit input/output assertions.
- Integration test: start `FeatureBuilder` against mock CLOB + Binance data, verify 3 consecutive snapshots are written to `FeatureStore`.

---

## Out of Scope

- Training any probability or regime model (Sprint 14, 15).
- Cross-sectional aggregation across multiple markets (Sprint 16).
- Wallet intelligence features (Sprint 17).
- Modifying the equity feature pipeline (`pipeline.py`) — equity features remain unchanged.

---

## Implementation Order

1. **Schemas** — `FeatureSnapshot` and `FeatureRecord` Pydantic models + `packages/common` updates.
2. **Data sources** — `clob.py` WebSocket buffer + REST polling; `binance.py` klines + futures polling.
3. **Feature computation** — `builder.py` with all 4 families; unit-test each family independently.
4. **FeatureStore** — Alembic migration + `store.py` read/write.
5. **Integration** — Wire `FeatureBuilder` into `session.py`; update `PolymarketMMStrategy.on_market_data`.
6. **API** — `features.py` router + register in FastAPI app.
7. **Tests** — Unit + integration coverage to AC-7.

---

## Recommended Skills

| Task | Skill |
|------|-------|
| Feature formula design, PnL decomposition definitions | `quant-analyst` |
| Async WebSocket ingestion, heartbeat, reconnect logic | `async-python-patterns` |
| Feature store design, TimescaleDB hypertable | `data-engineering-data-pipeline` |
| FastAPI router, Pydantic v2 schema patterns | `fastapi-pro`, `backend-dev-guidelines` |
| Pytest fixtures, mock WebSocket data, async test patterns | `python-testing-patterns` |

---

## Risk Notes

- **Stale Binance data**: if the 1m kline poll lags behind real time, `btc_distance_to_open` and RV features will be stale. Mitigate by timestamping each source independently and flagging `FeatureSnapshot.data_staleness` if any source exceeds 30s.
- **Polymarket heartbeat**: `FeatureBuilder` runs independently of the trading session but shares the CLOB WebSocket. If the MM session's heartbeat fails, the WebSocket connection drops, invalidating orderbook state. Design the feature builder with its own WebSocket connection or reconnect logic.
- **Regime label instability**: discrete regime labels can flip rapidly. Apply a minimum-hold filter (e.g., require 3 consecutive ticks in a new regime before switching label) to avoid noise in downstream consumers.
