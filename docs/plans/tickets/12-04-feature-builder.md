# Ticket: 12-04-feature-builder

## Task
Implement `services/features/polymarket/builder.py`: an async `FeatureBuilder` that runs on a 5-second tick cadence, pulls from `CLOBSource` and `BinanceSource`, computes all 4 feature families, and publishes `FeatureSnapshot` to an `asyncio.Queue`.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/features/polymarket/builder.py`
- Modify: `services/features/polymarket/__init__.py` (export `FeatureBuilder`)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-12-feature-layer-spec.md` (all Feature Families tables + FeatureBuilder section + Risk Notes)
- `docs/research/regime-allocation.md` (regime definitions, VPIN proxy, toxicity)

### Optional read-only references
- `docs/research/microstructure-model.md` (State variables, PnL decomposition formulas — for feature formula verification)
- `docs/research/probabilities.md` (btc_distance_to_open, RV windows, sign persistence definitions)
- `services/features/polymarket/sources/clob.py` (CLOBSource interface — read-only)
- `services/features/polymarket/sources/binance.py` (BinanceSource interface — read-only)
- `packages/common/polymarket_schemas.py` (FeatureSnapshot field names — read-only)

## Agent type
backend-agent

## Skill pack
- `async-python-patterns` (asyncio.Queue, background tasks, tick cadence)

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 4
- Max total tool calls: 14

## Done criteria

**`FeatureBuilder` class in `builder.py`:**

*Initialization:*
- `__init__(clob: CLOBSource, binance: BinanceSource, tick_seconds: float = 5.0)`
- `output_queue: asyncio.Queue[FeatureSnapshot]` — downstream consumers subscribe to this
- Internal rolling trade tape buffer (deque, max 300 entries) for `trade_flow_imbalance_1m` and `trade_flow_imbalance_5m`
- Internal regime hold buffer: tracks last 3 regime labels per family for minimum-hold filter (spec risk note)

*Lifecycle:*
- `async def start() -> None` — launches tick loop as background task; also starts CLOBSource and BinanceSource
- `async def stop() -> None` — cancels background tasks

*Tick loop (`_tick` coroutine):*
- Runs every `tick_seconds` (asyncio.sleep)
- Calls `_compute_snapshot()` → puts result on `output_queue` (non-blocking, drops if full)

*Feature computation (`_compute_snapshot() -> FeatureSnapshot`):*

**Family 1 — Market State (from CLOBSource):**
- `mid_price = (best_bid + best_ask) / 2`
- `implied_probability`: midpoint if spread ≤ 0.10, else `last_trade_price`
- `spread = best_ask - best_bid`
- `spread_bps = spread / mid_price * 10000`
- `time_to_close_seconds`: from market metadata passed at init
- `time_since_open_seconds`: `now - market_open_ts`
- `book_depth_bid_5tick` and `book_depth_ask_5tick`: from `CLOBSource.get_orderbook_state()`
- `time_since_last_trade`: `now - last_trade_ts`
- `time_since_last_price_change`: `now - last_price_change_ts`

**Family 2 — Microstructure:**
- `order_book_imbalance = (depth_bid - depth_ask) / (depth_bid + depth_ask)` — uses `book_depth_bid_5tick` / `book_depth_ask_5tick`
- `trade_flow_imbalance_1m` and `trade_flow_imbalance_5m`: from rolling trade tape (buy_vol - sell_vol over window)
- `last_5min_volume_share`: fraction of rolling window volume in last 5 min
- `aggressor_buy_fraction_1m`: fraction of recent trades tagged as buys
- `vpin_proxy = |buy_vol - sell_vol| / total_vol` over rolling bucket
- `fee_rate_current` from `CLOBSource.fetch_fee_rate()`
- `reward_eligible`, `reward_max_spread`, `reward_min_size` from `CLOBSource.fetch_reward_config()`

**Family 3 — Probabilistic (from BinanceSource):**
- `btc_distance_to_open = ln(btc_price_now / btc_hour_open)`
- `btc_rv_1m`, `btc_rv_5m`, `btc_rv_15m`: sum of squared log-returns over respective windows
- `btc_momentum_5m`: log return over last 5 minutes
- `btc_sign_persistence_5m`: fraction of positive 1m returns in last 5 minutes
- `btc_funding_rate` and `btc_basis_proxy`: from `BinanceSource.get_premium_index()`

**Family 4 — Regime (discrete labels with minimum-hold filter):**
- `vol_regime`: "low" / "medium" / "high" based on `btc_rv_1m` vs thresholds (configurable, default: low < 0.0001, high > 0.001)
- `trend_regime`: "trending" / "mean_reverting" / "neutral" from `btc_sign_persistence_5m` (> 0.7 → trending, < 0.3 → mean_reverting)
- `time_bucket`: "early" (0–20 min), "mid" (20–40 min), "late" (40–60 min) based on `time_since_open_seconds`
- `near_close_flag`: True if `time_to_close_seconds` ≤ 600
- `toxicity_regime`: "low" / "medium" / "high" from `vpin_proxy` (< 0.2 low, > 0.4 high)
- `spread_regime`: "tight" / "normal" / "wide" — compare `spread` against rolling 24h median (internal deque of spread history); defaults to "normal" on cold start
- `liquidity_score = book_depth_bid_5tick / (spread * btc_rv_5m + 1e-9)` (normalized 0–1 via min-max over rolling history)
- `competitive_pressure = 1 / (spread_bps + 1e-9)` (normalized)
- Regime minimum-hold: each discrete label only flips after 3 consecutive ticks agree on the new label

*Staleness check:*
- Sets `data_staleness_flag = True` if any source's `source_timestamp` is > 30s old

*Determinism:*
- All computation uses only data passed in from sources (no `datetime.now()` inside formulas — pass `captured_at` as parameter)
- Works identically whether `CLOBSource`/`BinanceSource` are live or mock/replayed implementations

**`services/features/polymarket/__init__.py`** exports `FeatureBuilder`

**`docs/plans/PROGRESS.md`** updated
