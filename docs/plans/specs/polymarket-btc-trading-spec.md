# Polymarket BTC Hourly Market Making — Feature Spec

**Date:** 2026-03-25
**Status:** Draft — awaiting user approval
**Sprint:** 10 (Polymarket Integration)

---

## 1. Vision and goals

### What we're building

A new **Polymarket trading service** for Caliper that market-makes on hourly BTC "Up/Down" binary markets. The service runs as a parallel, self-contained system alongside the existing equity/options infrastructure, sharing TimescaleDB and the dashboard/API layer for unified observability.

### Strategic path

| Phase | Description | Capital | Duration |
|---|---|---|---|
| **Phase 1 (V1)** | Market-making bot with fixed spread, post-only quoting, safety rails. One fixed hourly window per day. Dust capital (~$50-100). | Real, minimal | 4-8 weeks of daily runs |
| **Phase 2** | Add inventory skew, dynamic spread, fee-curve optimization, reward tracking, PnL decomposition. Tune parameters from Phase 1 data. | Small (~$200-500) | Ongoing iteration |
| **Phase 3** | Layer directional probability model (hybrid C strategy). Model estimates true P(Up) from Binance price path, skews quoting based on model confidence. | Moderate (scaled by conviction) | After sufficient data |

### Success criteria for Phase 1

- Bot places real post-only orders on Polymarket with dust capital
- Heartbeat loop keeps orders alive; cancel-all fires on any error
- All orderbook snapshots, fills, PnL, and session metadata are recorded to TimescaleDB
- Bot runs reliably for one fixed hourly window per day from local machine
- Dashboard and API can show Polymarket session history and basic PnL
- No uncontrolled capital loss (strict inventory cap, post-only enforcement)

### Non-goals for V1

- Directional model / probability estimation (Phase 3)
- Dynamic window selection / reward-density optimization (Phase 2+)
- Cloud deployment / always-on hosting
- Mobile dashboard views
- Multi-market concurrent quoting

---

## 2. Architecture

### 2.1 Service structure

The Polymarket service lives under `services/polymarket/` as a self-contained Python service with its own entry point, event loop, and execution logic. It does **not** extend the existing Strategy ABC or equity OMS — binary market making is architecturally distinct from equity signal generation.

```
services/polymarket/
├── __init__.py
├── config.py                # Service configuration (Pydantic settings)
├── main.py                  # Entry point: scheduler + session orchestrator
├── session.py               # Single trading session lifecycle (one hourly window)
│
├── market_discovery.py      # Gamma API: find today's target hourly BTC market
├── data_feed.py             # WebSocket + Binance price ingestion, orderbook tracking
├── quoting_engine.py        # Core quoting logic: midpoint, spread, inventory skew
├── executor.py              # CLOB order placement, cancel, replace, heartbeat loop
├── safety.py                # Cancel-all, inventory cap, error handler, session kill switch
├── recorder.py              # Write all data to TimescaleDB
│
├── wallet.py                # Wallet management: signing, USDC split/merge, balance checks
├── schemas.py               # Polymarket-specific Pydantic models (internal)
├── fee_model.py             # Fee curve computation (taker fees, maker rebates)
├── constants.py             # API URLs, fee parameters, tick sizes, timing constants
│
├── adapters/
│   ├── __init__.py
│   ├── gamma_client.py      # Gamma API client (market discovery)
│   ├── clob_client.py       # CLOB REST + WebSocket client (orders, book, heartbeat)
│   ├── data_api_client.py   # Data API client (trades, activity, rebates)
│   └── binance_client.py    # Binance spot klines + futures funding data
│
└── pyproject.toml           # Service-level dependencies
```

### 2.2 Relationship to existing Caliper services

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Caliper Platform                                │
│                                                                         │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────────┐  │
│  │ services/api     │   │ services/risk    │   │ services/execution │  │
│  │ (FastAPI)        │   │ (RiskManager)    │   │ (Alpaca OMS)       │  │
│  │                  │   │                  │   │                    │  │
│  │ + new routers:   │   │ Equity-only;     │   │ Equity-only;       │  │
│  │   /v1/polymarket │   │ PM has own       │   │ PM has own         │  │
│  │                  │   │ safety layer     │   │ executor           │  │
│  └───────┬──────────┘   └──────────────────┘   └────────────────────┘  │
│          │                                                              │
│          │ reads                                                        │
│          ▼                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    TimescaleDB (shared)                          │   │
│  │                                                                  │   │
│  │  Equity tables:              Polymarket tables (new):            │   │
│  │  market_data.price_bars      pm.sessions                        │   │
│  │  execution.orders            pm.orders                          │   │
│  │  execution.positions         pm.fills                           │   │
│  │  backtests.strategy_runs     pm.orderbook_snapshots             │   │
│  │  ...                         pm.binance_candles                 │   │
│  │                              pm.pnl_snapshots                   │   │
│  │                              pm.market_metadata                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│          ▲                                                              │
│          │ writes                                                       │
│          │                                                              │
│  ┌──────────────────┐   ┌──────────────────┐                           │
│  │ services/         │   │ apps/dashboard   │                           │
│  │ polymarket        │   │ (Next.js)        │                           │
│  │ (new service)     │   │                  │                           │
│  │                   │   │ + PM session     │                           │
│  │ Runs locally      │   │   status page    │                           │
│  │ during target     │   │   (future)       │                           │
│  │ hourly window     │   │                  │                           │
│  └───────────────────┘   └──────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key architectural principles:**

1. **Self-contained execution.** The Polymarket service runs independently. It doesn't depend on the API server, dashboard, or equity services being up. It only needs DB access.
2. **Shared observability.** The API service reads Polymarket data from `pm.*` tables and exposes it through new routers. The dashboard consumes those endpoints.
3. **Separate safety model.** Polymarket uses heartbeat + cancel-all + inventory cap instead of the equity RiskManager/CircuitBreaker. The concepts map (both fail-safe by default), but the implementations are distinct because the failure modes are different (WebSocket disconnection vs broker API failure).
4. **No Strategy ABC.** Binary market making doesn't follow the `on_market_data → generate_signals → risk_check → Order` pipeline. It's a continuous quoting loop with real-time state. Forcing it into the equity interface would create impedance mismatch.

### 2.3 Execution flow for a single session

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Session Lifecycle (one hourly window)                  │
└─────────────────────────────────────────────────────────────────────────┘

  main.py (scheduler)
    │
    │  T-5min: wake up, begin pre-session
    ▼
  market_discovery.py
    │  Find today's target market via Gamma API
    │  Resolve condition_id, token_ids, tick_size, feesEnabled
    │  Fetch Binance 1H candle open price
    ▼
  session.py — PRE-SESSION
    │  Check wallet balance (USDC.e)
    │  Split USDC.e into YES/NO pairs if needed
    │  Validate fee regime (query /fee-rate)
    │  Initialize recorder (open DB session)
    ▼
  session.py — ACTIVE TRADING (T+0 to T+55min)
    │
    │  ┌─────── concurrent loops ───────┐
    │  │                                │
    │  │  data_feed.py                  │  executor.py
    │  │  - CLOB WebSocket: book,       │  - Heartbeat loop (every 5s)
    │  │    price_change, trades        │  - Place/replace post-only
    │  │  - Binance price stream        │    bid and ask around mid
    │  │  - Update midpoint, spread,    │  - Cancel stale quotes
    │  │    best bid/ask state          │  - Enforce post-only (reject
    │  │                                │    if would cross)
    │  │  quoting_engine.py             │
    │  │  - Compute mid from book       │  safety.py
    │  │  - Apply spread offset (δ)     │  - Inventory cap check
    │  │  - V1: fixed symmetric spread  │  - Cancel-all on any error
    │  │  - V2: inventory skew          │  - Session kill switch
    │  │                                │
    │  │  recorder.py                   │
    │  │  - Log orderbook snapshots     │
    │  │  - Log fills as they arrive    │
    │  │  - Log PnL snapshots           │
    │  │                                │
    │  └────────────────────────────────┘
    │
    ▼
  session.py — WIND-DOWN (T+55min to T+60min)
    │  Cancel all open orders
    │  Stop placing new quotes
    │  Let remaining fills settle
    ▼
  session.py — POST-SESSION
    │  Record final PnL (mark-to-market or settlement)
    │  Merge matched YES/NO pairs back to USDC.e (only equal pairs can merge)
    │  Log residual unmatched tokens (e.g., 100 YES left over)
    │  Residual tokens are left for resolution — if outcome is YES/Up,
    │    they redeem for $1 each; if DOWN, they expire worthless
    │  Write session summary to pm.sessions (including residual inventory)
    │  Log to stdout
    ▼
  main.py — session complete, exit
```

**Timing rationale for wind-down at T+55min:** The research shows that toxic flow (informed directional takers) increases sharply in the last 5 minutes as the candle outcome becomes more predictable. Pulling quotes early avoids adverse selection in the most dangerous period. This threshold is configurable and should be tuned based on Phase 1 data.

---

## 3. Data model

All Polymarket tables live in a `pm` schema within the shared TimescaleDB instance. Table names are prefixed to avoid collision with equity tables.

### 3.1 pm.sessions

Tracks each daily trading session (one per hourly window).

```sql
CREATE TABLE pm.sessions (
    session_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_condition_id VARCHAR(100) NOT NULL,
    market_slug         TEXT,
    token_id_yes        VARCHAR(100) NOT NULL,
    token_id_no         VARCHAR(100) NOT NULL,
    window_start        TIMESTAMP WITH TIME ZONE NOT NULL,
    window_end          TIMESTAMP WITH TIME ZONE NOT NULL,
    binance_open_price  DECIMAL(20, 8),
    binance_close_price DECIMAL(20, 8),
    outcome             VARCHAR(10) CHECK (outcome IN ('UP', 'DOWN')),  -- nullable

    initial_usdc        DECIMAL(20, 8) NOT NULL,
    final_usdc          DECIMAL(20, 8),
    realized_pnl        DECIMAL(20, 8),
    spread_capture_pnl  DECIMAL(20, 8),
    inventory_drift_pnl DECIMAL(20, 8),
    -- Rebate and reward fields are NULL in V1; populated in Phase 2
    -- when daily payout attribution from Data API is implemented.
    -- Daily payouts arrive at midnight UTC and apply to the full day,
    -- not individual sessions.
    maker_rebate_pnl    DECIMAL(20, 8),
    liquidity_reward_pnl DECIMAL(20, 8),
    gas_costs_matic     DECIMAL(20, 8),
    gas_costs_usdc      DECIMAL(20, 8),

    total_orders_placed INTEGER DEFAULT 0,
    total_fills         INTEGER DEFAULT 0,
    total_volume_usdc   DECIMAL(20, 8) DEFAULT 0,
    avg_spread_quoted   DECIMAL(10, 6),
    max_inventory_held  DECIMAL(20, 8),
    wind_down_time_min  INTEGER,

    fee_regime          VARCHAR(20),
    fees_enabled        BOOLEAN,
    
    -- Session regime tagging (Improvement 2)
    volatility_regime   VARCHAR(10) CHECK (volatility_regime IN ('LOW', 'MEDIUM', 'HIGH')),
    spread_regime       VARCHAR(10) CHECK (spread_regime IN ('TIGHT', 'WIDE')),
    volume_regime       VARCHAR(10) CHECK (volume_regime IN ('LOW', 'MEDIUM', 'HIGH')),
    btc_trend_regime    VARCHAR(10) CHECK (btc_trend_regime IN ('UP', 'DOWN', 'FLAT')),

    config_snapshot     JSONB,
    status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                        CHECK (status IN ('PENDING', 'ACTIVE', 'WIND_DOWN',
                                          'COMPLETED', 'ERROR', 'KILLED')),
    error_message       TEXT,
    started_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at        TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_pm_sessions_window ON pm.sessions (window_start DESC);
```

### 3.2 pm.orders

Tracks every order placed on Polymarket during a session. This is a regular table (not a hypertable) because order volume per session is low and UUID-based lookups + FK references from `pm.fills` are needed.

```sql
CREATE TABLE pm.orders (
    order_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES pm.sessions(session_id),
    polymarket_order_id VARCHAR(200),
    token_id            VARCHAR(100) NOT NULL,
    side                VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    price               DECIMAL(10, 4) NOT NULL,
    original_size       DECIMAL(20, 8) NOT NULL,
    filled_size         DECIMAL(20, 8) NOT NULL DEFAULT 0,
    order_type          VARCHAR(20) NOT NULL DEFAULT 'GTC',
    post_only           BOOLEAN NOT NULL DEFAULT TRUE,
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING', 'LIVE', 'PARTIALLY_MATCHED',
                                          'MATCHED', 'CANCELLED', 'REJECTED')),
    placed_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    filled_at           TIMESTAMP WITH TIME ZONE,
    cancelled_at        TIMESTAMP WITH TIME ZONE,
    reject_reason       TEXT,
    fee_paid            DECIMAL(20, 8) DEFAULT 0,
    midpoint_at_place   DECIMAL(10, 4),
    spread_at_place     DECIMAL(10, 4),
    
    -- Fill-to-quote attribution (Gap 4)
    time_on_book_seconds DECIMAL(10, 2),      -- How long order was live before first fill or cancel
    quote_version_id     INTEGER,              -- Incremental counter per session to track quote generations
    queue_ahead_at_place DECIMAL(20, 8)       -- Estimated queue position when placed
);

CREATE INDEX idx_pm_orders_session ON pm.orders (session_id, placed_at DESC);
CREATE INDEX idx_pm_orders_status ON pm.orders (status) WHERE status IN ('PENDING', 'LIVE');
CREATE INDEX idx_pm_orders_version ON pm.orders (session_id, quote_version_id);
```

**Partial fill handling:** When a partial fill arrives, `filled_size` is incremented and status moves to `PARTIALLY_MATCHED`. The order stays `LIVE` on Polymarket's book for the remaining size. When fully filled, status becomes `MATCHED`. If cancelled after partial fill, status becomes `CANCELLED` with the final `filled_size` preserved.

**Quote version tracking (Gap 4):** Each cancel/replace cycle increments `quote_version_id` within the session. This lets you analyze which quote generation got filled and how long quotes need to be live before fills arrive.

### 3.3 pm.fills

Tracks actual fills (could be partial matches of orders). Regular table (not hypertable) — fill volume is low and FK reference to `pm.orders` requires stable UUID PK.

```sql
CREATE TABLE pm.fills (
    fill_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES pm.sessions(session_id),
    order_id            UUID REFERENCES pm.orders(order_id),
    token_id            VARCHAR(100) NOT NULL,
    side                VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    price               DECIMAL(10, 4) NOT NULL,
    size                DECIMAL(20, 8) NOT NULL,
    fee                 DECIMAL(20, 8) DEFAULT 0,
    is_maker            BOOLEAN NOT NULL DEFAULT TRUE,
    filled_at           TIMESTAMP WITH TIME ZONE NOT NULL,
    midpoint_at_fill    DECIMAL(10, 4),
    binance_price_at_fill DECIMAL(20, 8),
    inventory_after     DECIMAL(20, 8),
    
    -- Adverse selection labeling (Gap 2)
    midpoint_5s_after   DECIMAL(10, 4),       -- Midpoint 5 seconds after fill
    midpoint_10s_after  DECIMAL(10, 4),       -- Midpoint 10 seconds after fill
    edge_at_fill        DECIMAL(10, 6),       -- (fill_price - midpoint_at_fill) * direction
    edge_5s_after       DECIMAL(10, 6),       -- (fill_price - midpoint_5s_after) * direction
    adverse_selection_flag BOOLEAN,           -- TRUE if edge_5s_after < 0 (fill went against us)
    
    -- Attribution to quote version (Gap 4)
    quote_version_id    INTEGER,              -- Which quote generation caused this fill
    time_on_book_before_fill DECIMAL(10, 2)  -- How long the order was live before this fill
);

CREATE INDEX idx_pm_fills_session ON pm.fills (session_id, filled_at DESC);
CREATE INDEX idx_pm_fills_order ON pm.fills (order_id);
CREATE INDEX idx_pm_fills_adverse ON pm.fills (session_id, adverse_selection_flag) WHERE adverse_selection_flag = TRUE;
```

**Adverse selection tracking (Gap 2):** The `midpoint_5s_after` and `midpoint_10s_after` fields are populated asynchronously after the fill (the recorder waits 5s/10s, then fetches the current midpoint and updates the row). The `adverse_selection_flag` is set to TRUE if the midpoint moved against us within 5 seconds, indicating we were picked off by informed flow. This is the primary signal for toxic flow detection and wind-down optimization.

### 3.4 pm.orderbook_snapshots

Periodic snapshots of the Polymarket orderbook state for analysis.

```sql
CREATE TABLE pm.orderbook_snapshots (
    snapshot_id         BIGSERIAL,
    session_id          UUID NOT NULL REFERENCES pm.sessions(session_id),
    timestamp           TIMESTAMP WITH TIME ZONE NOT NULL,
    best_bid            DECIMAL(10, 4),
    best_ask            DECIMAL(10, 4),
    midpoint            DECIMAL(10, 4),
    spread              DECIMAL(10, 4),
    bid_depth_1pct      DECIMAL(20, 8),
    ask_depth_1pct      DECIMAL(20, 8),
    imbalance           DECIMAL(10, 6),
    binance_price       DECIMAL(20, 8),
    distance_to_open    DECIMAL(10, 6),
    
    -- Our quotes
    our_bid_price       DECIMAL(10, 4),
    our_ask_price       DECIMAL(10, 4),
    our_bid_size        DECIMAL(20, 8),
    our_ask_size        DECIMAL(20, 8),
    
    -- Queue position tracking (Gap 1)
    our_bid_queue_ahead_size DECIMAL(20, 8),  -- Total size at our bid price ahead of us in queue
    our_ask_queue_ahead_size DECIMAL(20, 8),  -- Total size at our ask price ahead of us in queue
    num_orders_at_best_bid   INTEGER,         -- Competition proxy (Gap 5)
    num_orders_at_best_ask   INTEGER,
    total_depth_top_3_levels DECIMAL(20, 8),  -- Sum of size in top 3 price levels each side
    
    -- Inventory
    inventory_yes       DECIMAL(20, 8),
    inventory_no        DECIMAL(20, 8),
    inventory_value_mid DECIMAL(20, 8),       -- Mark inventory at midpoint (Gap 3 clarification)
    
    -- Reward eligibility tracking (Gap 3)
    is_within_reward_spread BOOLEAN,          -- Are our quotes within max_incentive_spread?
    is_above_min_size       BOOLEAN,          -- Are our quotes >= min_incentive_size?
    estimated_reward_score  DECIMAL(10, 6),   -- Estimated Q_min score (if computable)
    
    PRIMARY KEY (snapshot_id, timestamp)
);

SELECT create_hypertable('pm.orderbook_snapshots', 'timestamp',
                         chunk_time_interval => INTERVAL '1 hour');
```

### 3.5 pm.binance_candles

Store Binance 1H candle data aligned to Polymarket market windows.

```sql
CREATE TABLE pm.binance_candles (
    candle_id           BIGSERIAL,
    open_time           TIMESTAMP WITH TIME ZONE NOT NULL,
    close_time          TIMESTAMP WITH TIME ZONE NOT NULL,
    open                DECIMAL(20, 8) NOT NULL,
    high                DECIMAL(20, 8) NOT NULL,
    low                 DECIMAL(20, 8) NOT NULL,
    close               DECIMAL(20, 8) NOT NULL,
    volume              DECIMAL(30, 8),
    source              VARCHAR(20) DEFAULT 'binance',
    PRIMARY KEY (candle_id, open_time)
);

SELECT create_hypertable('pm.binance_candles', 'open_time',
                         chunk_time_interval => INTERVAL '1 day');
```

### 3.6 pm.pnl_snapshots

Intra-session PnL tracking for time-series analysis.

```sql
CREATE TABLE pm.pnl_snapshots (
    snapshot_id         BIGSERIAL,
    session_id          UUID NOT NULL REFERENCES pm.sessions(session_id),
    timestamp           TIMESTAMP WITH TIME ZONE NOT NULL,
    mark_to_market_pnl  DECIMAL(20, 8),
    realized_pnl        DECIMAL(20, 8),
    spread_capture      DECIMAL(20, 8),
    inventory_value     DECIMAL(20, 8),
    cash_balance        DECIMAL(20, 8),
    PRIMARY KEY (snapshot_id, timestamp)
);

SELECT create_hypertable('pm.pnl_snapshots', 'timestamp',
                         chunk_time_interval => INTERVAL '1 hour');
```

### 3.7 pm.market_metadata

Cache of market discovery results for historical reference.

```sql
CREATE TABLE pm.market_metadata (
    condition_id        VARCHAR(100) PRIMARY KEY,
    slug                TEXT,
    question            TEXT,
    token_id_yes        VARCHAR(100),
    token_id_no         VARCHAR(100),
    window_start        TIMESTAMP WITH TIME ZONE,
    window_end          TIMESTAMP WITH TIME ZONE,
    tick_size           DECIMAL(10, 4),
    fees_enabled        BOOLEAN,
    fee_rate_bps        DECIMAL(10, 4),
    rewards_max_spread  DECIMAL(10, 4),
    rewards_min_size    DECIMAL(20, 8),
    total_volume        DECIMAL(20, 8),
    discovered_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3.8 pm.toxic_flow_by_minute

Tracks adverse selection rate by minute within the hour for wind-down optimization (Improvement 3).

```sql
CREATE TABLE pm.toxic_flow_by_minute (
    session_id          UUID NOT NULL REFERENCES pm.sessions(session_id),
    minute_offset       INTEGER NOT NULL CHECK (minute_offset >= 0 AND minute_offset < 60),
    total_fills         INTEGER DEFAULT 0,
    adverse_fills       INTEGER DEFAULT 0,
    adverse_fill_pct    DECIMAL(5, 2),
    avg_edge_realized   DECIMAL(10, 6),
    PRIMARY KEY (session_id, minute_offset)
);
```

**Usage:** After each session, compute per-minute adverse selection rates. Over time, this builds a curve showing when toxic flow spikes (likely in the last 5-10 minutes). This data directly informs the optimal `wind_down_minutes` parameter.

### 3.9 Regime tagging computation

The session regime fields (`volatility_regime`, `spread_regime`, `volume_regime`, `btc_trend_regime`) are computed at session end from the recorded data:

| Regime | Computation | Thresholds (V1 defaults, tune from data) |
|---|---|---|
| `volatility_regime` | Realized volatility from Binance 1H candle: `σ = √(Σ(r_i²))` over 1-minute returns | LOW: σ < 0.01, MEDIUM: 0.01-0.03, HIGH: >0.03 |
| `spread_regime` | Average spread from `pm.orderbook_snapshots`: `avg(spread)` | TIGHT: <0.02, WIDE: ≥0.02 |
| `volume_regime` | Total market volume from Polymarket market metadata or Data API trades | LOW: <$50K, MEDIUM: $50K-$150K, HIGH: >$150K |
| `btc_trend_regime` | `(close - open) / open` from Binance 1H candle | UP: >0.5%, DOWN: <-0.5%, FLAT: between |

These tags enable regime-specific performance analysis (e.g., "Do we lose money in HIGH volatility sessions?" or "Is TIGHT spread regime more profitable?").

---

## 4. Data model validation — what writes where

This table confirms full coverage between components and tables.

| Component | Writes to | What |
|---|---|---|
| `market_discovery.py` | `pm.market_metadata` | Market metadata on discovery |
| `recorder.py` | `pm.sessions` | Session record (start and end) |
| `executor.py` → `recorder.py` | `pm.orders` | Every order placed, with quote version and queue position |
| `executor.py` → `recorder.py` | `pm.fills` | Every fill received (immediate); adverse selection fields updated async |
| `data_feed.py` → `recorder.py` | `pm.orderbook_snapshots` | Periodic snapshots with queue position, competition, reward eligibility |
| `data_feed.py` → `recorder.py` | `pm.pnl_snapshots` | Periodic PnL breakdown |
| `data_feed.py` → `recorder.py` | `pm.binance_candles` | Binance 1H candle at session start/end |
| `session.py` → `recorder.py` | `pm.toxic_flow_by_minute` | Post-session computation from fills |

**Key analysis-enabling data (addresses all gaps):**

| Analysis need | Enabled by |
|---|---|
| Queue position optimization | `our_bid_queue_ahead_size`, `our_ask_queue_ahead_size` in snapshots |
| Toxic flow detection | `adverse_selection_flag`, `edge_5s_after` in fills |
| Wind-down timing optimization | `pm.toxic_flow_by_minute` table |
| Reward eligibility verification | `is_within_reward_spread`, `is_above_min_size` in snapshots |
| Fill-to-quote attribution | `quote_version_id`, `time_on_book_seconds` in orders |
| Competition tracking | `num_orders_at_best_bid/ask`, `total_depth_top_3_levels` in snapshots |
| Quote stickiness analysis | `quote_version_id` + `time_on_book_seconds` across orders |
| Fill probability modeling | `(price - midpoint_at_place)` in orders + fill outcomes |
| Regime-specific performance | `volatility_regime`, `spread_regime`, `volume_regime` in sessions |

---

## 5. V1 parameter choices and tuning strategy

These parameters are set conservatively for V1 and should be tuned from Phase 1 data.

| Parameter | V1 value | Rationale | Tuning signal |
|---|---|---|---|
| `requote_interval_seconds` | 10s | Conservative — avoids over-canceling and losing queue position | Analyze `time_on_book_seconds` distribution: if median fill time is 20s+, can requote faster; if fills arrive in <10s, slow down |
| `quote_spread` | 0.02 (2 cents) | Wide enough to capture spread, tight enough to compete | Analyze fill rate vs spread: if no fills, tighten; if high adverse selection, widen |
| `quote_size` | 50 shares | Small enough for dust capital (~$25 per side), large enough to be meaningful | Phase 2: size dynamically based on fill quality and inventory |
| `inventory_cap` | 200 shares | Limits directional exposure to ~$100 at p=0.50 | If inventory never approaches cap, can increase; if frequently capped, decrease or add inventory skew |
| `wind_down_minutes` | 5 | Avoids last-minute toxic flow | Tune from `pm.toxic_flow_by_minute`: if adverse selection spikes at T-10min, widen to 10; if flat until T-2min, tighten to 2 |

**Quote size rationale (Question 2):** Fixed at 50 shares for V1 to keep capital requirements low and simplify analysis. Phase 2 can introduce dynamic sizing:
- Smaller size early in the hour (lower risk, faster learning)
- Larger size mid-hour when spread is tight and volatility is low
- Smaller size again near close when toxicity increases

**Requote interval rationale (Question 1):** 10 seconds is a conservative starting point. The data you collect will show:
- If fills consistently arrive within 5-10 seconds → you can requote more aggressively
- If most fills take 20+ seconds → you're canceling prematurely and losing queue priority
- If adverse selection is high → you're requoting too slowly and getting picked off

The `time_on_book_seconds` and `quote_version_id` fields in `pm.orders` are specifically designed to answer this question empirically.

---

## 6. Core components — V1 detailed design

### 4.0 Key design clarifications

**Inventory definition (Question 3):**
- **Primary inventory:** YES token count (net long position in YES)
- **Inventory value:** Marked at midpoint (`inventory_yes × midpoint`) for PnL snapshots
- **Hedge inventory:** NO tokens from initial split are held as a hedge (form complete sets with YES)
- **Net exposure:** `inventory_yes - inventory_no` shares (if perfectly hedged, this is 0)
- **Inventory cap:** Limits `inventory_yes` to prevent runaway directional exposure

**Binance feed choice (Question 4):**
- **V1:** HTTP polling every 5 seconds via `/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=1`
- **Rationale:** Simple, reliable, sufficient latency for hourly market making
- **Phase 2:** Upgrade to Binance WebSocket stream (`wss://stream.binance.com:9443/ws/btcusdt@kline_1m`) for sub-second price updates when directional model requires tighter timing edge

### 4.1 Configuration (`config.py`)

```python
class PolymarketConfig(BaseSettings):
    # Wallet
    private_key: SecretStr             # Polygon wallet private key
    wallet_address: str                # Public address

    # Target window — specified in local time, converted to UTC at runtime
    # using zoneinfo. This handles DST transitions automatically.
    target_hour_local: int = 9         # 9 AM in target_timezone
    target_timezone: str = "America/New_York"  # IANA timezone name
    pre_session_minutes: int = 5
    wind_down_minutes: int = 5

    # Quoting parameters
    quote_spread: Decimal = Decimal("0.02")    # 2 cents each side of mid (V1 fixed; tune from data)
    quote_size: Decimal = Decimal("50")         # 50 shares per side (V1 fixed; Phase 2 can size dynamically)
    inventory_cap: Decimal = Decimal("200")     # Max YES shares held (net directional exposure limit)
    requote_interval_seconds: int = 10          # V1 default: 10s (conservative to avoid over-canceling)
                                                # Tune based on time_on_book_seconds analysis:
                                                # - Too slow (>10s) → lose queue position to competition
                                                # - Too fast (<5s) → cancel before fills arrive
                                                # Start at 10s, log everything, adjust quickly

    # Safety
    max_session_loss_usdc: Decimal = Decimal("20")
    heartbeat_interval_seconds: int = 5
    cancel_all_on_error: bool = True

    # Recording
    snapshot_interval_seconds: int = 5

    # Database
    database_url: str

    # API URLs (defaults to production)
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    clob_api_url: str = "https://clob.polymarket.com"
    data_api_url: str = "https://data-api.polymarket.com"
    clob_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    binance_api_url: str = "https://api.binance.com"

    # Binance staleness threshold
    binance_stale_seconds: int = 30
```

### 6.2 Market discovery (`market_discovery.py`)

**Responsibility:** Find the exact Polymarket hourly BTC market for today's target window.

**V1 algorithm:**
1. Query Gamma API `GET /markets` with filters for active BTC hourly markets.
2. Parse market metadata to find the market whose window matches the configured `target_hour_utc`.
3. Extract `condition_id`, `token_id` for YES and NO outcomes, `minimum_tick_size`.
4. Query `/fee-rate?token_id={token_id}` to determine if fees are enabled and the current rate.
5. Write metadata to `pm.market_metadata`.
6. Return a `MarketInfo` object to the session.

**Edge cases:**
- Market not yet created (can happen if discovered too early) → retry with backoff.
- Multiple markets for the same hour → prefer the one with higher volume or most recent creation.
- Market already closed → skip session, log warning.

### 6.3 Data feed (`data_feed.py`)

**Responsibility:** Maintain real-time view of the Polymarket orderbook and Binance BTC price.

**Two concurrent feeds:**

1. **Polymarket CLOB WebSocket** — subscribe to `market` channel for the YES token. Process message types:
   - `book`: full orderbook snapshot → rebuild local book state
   - `price_change`: order addition/removal → update local book
   - `last_trade_price`: trade occurred → update last trade, detect fills
   - `tick_size_change`: tick size changed → update quoting constraints

2. **Binance price** — poll `GET /api/v3/klines?symbol=BTCUSDT&interval=1m&limit=1` every 5 seconds (or use WebSocket stream if latency matters). Track BTC price relative to the hour's open.

**Derived state (updated on every book change):**
- `best_bid`, `best_ask`, `midpoint`, `spread`
- `implied_probability` = midpoint (or last trade if spread > $0.10)
- `distance_to_open` = ln(current_BTC / hour_open_BTC)
- `time_remaining` = seconds until window close

### 6.4 Quoting engine (`quoting_engine.py`)

**Responsibility:** Decide what bid and ask to quote.

**Quoting model: YES token book only.**

The bot quotes exclusively on the YES token orderbook. A bid at 0.48 means "buy 50 YES shares at $0.48 each" (cost: $24 USDC). An ask at 0.52 means "sell 50 YES shares at $0.52 each" (receive: $26 USDC). Inventory tracks net YES token holdings — buying increases YES inventory, selling decreases it.

The initial USDC split (e.g., split 100 USDC.e → 100 YES + 100 NO) provides starting YES inventory for asks and USDC.e for bids. The NO tokens from the split are held as a hedge (they form a "complete set" with any YES tokens still held at resolution).

**V1 (fixed symmetric spread):**
```
bid_price = round_to_tick(midpoint - spread_offset)
ask_price = round_to_tick(midpoint + spread_offset)
bid_size = quote_size
ask_size = quote_size
```

Where:
- `midpoint` comes from the data feed's local book state
- `spread_offset` = `config.quote_spread / 2`
- `round_to_tick` snaps to the market's tick size

**Inventory check:** If current YES inventory >= `inventory_cap`, stop placing bids (don't accumulate more). If YES inventory <= 0 (sold all split tokens), stop placing asks (nothing to sell).

**V2 additions (documented for future, not built in V1):**
- **Inventory skew:** `center = midpoint - φ * inventory` (Avellaneda-Stoikov style)
- **Dynamic spread:** Widen when volatility is high or time-to-close is short
- **Fee-aware thresholds:** Don't quote inside the fee + spread deadzone
- **Directional model skew (Phase 3):** Shift center based on model probability

### 6.5 Executor (`executor.py`)

**Responsibility:** Place and manage orders on the Polymarket CLOB, maintain heartbeat.

**Core loop:**
1. Every `requote_interval_seconds`:
   - Get desired bid/ask from quoting engine
   - If current live orders differ from desired: cancel old, place new
   - Always use `postOnly: true` and `GTC` time-in-force
2. Every `heartbeat_interval_seconds`:
   - Send heartbeat to `/heartbeat` endpoint
   - Track `heartbeat_id` for session continuity
   - If heartbeat fails: log error, trigger cancel-all, retry

**Order signing:** All orders are EIP-712 signed using the configured private key. Use `py-clob-client` SDK or implement signing directly with `eth_account`.

**Cancel/replace strategy:** Rather than amending orders (not supported), cancel the stale order and place a new one. Batch cancels when possible. Handle rate limits with jittered backoff.

**HTTP 425 handling:** If CLOB returns 425 (engine restart), pause order management, retry with exponential backoff (1s, 2s, 4s), resume when successful.

### 6.6 Safety layer (`safety.py`)

**Responsibility:** Ensure the bot fails safe under all conditions.

**Safety rules (all enforced in V1):**

| Rule | Trigger | Action |
|---|---|---|
| **Post-only enforcement** | Order would cross spread | CLOB rejects it (platform-enforced); log and skip |
| **Inventory cap** | YES or NO inventory >= `inventory_cap` | Stop quoting the side that would increase inventory |
| **Session loss limit** | Unrealized + realized PnL < `-max_session_loss_usdc` | Cancel all orders, end session early |
| **Heartbeat failure** | Heartbeat response fails or times out | All open orders auto-cancelled by platform; bot attempts reconnect |
| **WebSocket disconnect** | CLOB WebSocket drops | Cancel all orders via REST, attempt reconnect, pause quoting until book state is fresh |
| **Any unhandled exception** | Uncaught error in main loop | Cancel all orders, log error, end session with status ERROR |
| **Wind-down timer** | `time_remaining < wind_down_minutes * 60` | Cancel all orders, stop quoting, let fills settle |
| **Binance feed stale** | No fresh Binance price update for >30 seconds | Pause quoting (cancel open orders), log warning, continue heartbeat; resume when feed recovers |
| **Manual kill** | User sends SIGINT/SIGTERM | Cancel all orders, write session summary, exit cleanly |

**Cancel-all implementation:** Call `DELETE /cancel-all` on the CLOB API. If the cancel-all REST call itself fails (network error, rate limit), the heartbeat timeout (~10s) serves as a platform-enforced backstop — orders are auto-cancelled when heartbeat lapses. The bot logs the cancel-all failure and does not attempt to place new orders. This is Polymarket's documented emergency endpoint. The bot calls it as the first action in any error path.

**Heartbeat discipline:** The platform cancels all open orders if a valid heartbeat isn't received within ~10 seconds (plus buffer). The bot sends heartbeats every 5 seconds. If a heartbeat fails, the bot assumes orders will be cancelled and does not place new orders until heartbeat is restored.

### 6.7 Recorder (`recorder.py`)

**Responsibility:** Write all session data to TimescaleDB.

**What gets recorded:**

| Data | Cadence | Table |
|---|---|---|
| Orderbook state (best bid/ask, mid, spread, depth, imbalance, our quotes, inventory, queue position, competition proxy, reward eligibility) | Every `snapshot_interval_seconds` (5s) | `pm.orderbook_snapshots` |
| Every order placed | On placement | `pm.orders` |
| Every fill received | On fill (immediate); adverse selection fields updated 5s/10s later | `pm.fills` |
| PnL breakdown (MTM, realized, spread capture, inventory value) | Every 30 seconds | `pm.pnl_snapshots` |
| Binance 1H candle data | At session start and end | `pm.binance_candles` |
| Session summary (including regime tags) | At session end | `pm.sessions` |
| Toxic flow by minute | At session end (computed from fills) | `pm.toxic_flow_by_minute` |
| Market metadata | At discovery time | `pm.market_metadata` |

**Write strategy:** Use async batch inserts for snapshots (buffer N rows, flush on interval or buffer full). Use immediate inserts for orders and fills (low frequency, high importance).

**Quote stickiness tracking (Improvement 1):** The `quote_version_id` in orders and the `time_on_book_seconds` field let you compute quote stickiness metrics post-session:
- Average time between requotes
- Fill rate vs time-on-book
- Correlation between cancel frequency and adverse selection

**Fill probability curve (Improvement 4):** With `(price - midpoint_at_place)` from orders and `filled_size > 0` as the outcome, you can build a logistic model of fill probability vs distance-from-mid. This becomes your core quoting model for Phase 2 dynamic spread optimization.

**Queue position estimation (Gap 1):** The CLOB WebSocket `book` message provides full depth arrays (`bids: [{price, size}, ...]`, `asks: [{price, size}, ...]`). When an order is placed at price `p`, the recorder sums all size at price `p` that arrived before your order (approximated by timestamp ordering or by tracking cumulative size at that level before your placement). This estimate is stored as `queue_ahead_at_place` in `pm.orders` and updated as `our_bid_queue_ahead_size` / `our_ask_queue_ahead_size` in snapshots. In V1, this is a rough estimate; Phase 2 can refine with order ID tracking if Polymarket exposes it.

**Adverse selection async update (Gap 2):** When a fill is recorded, the initial row is written immediately with `midpoint_at_fill` and `binance_price_at_fill`. The recorder spawns an async task that waits 5 seconds, fetches the current midpoint, and updates `midpoint_5s_after` and `edge_5s_after`. Same for 10 seconds. The `adverse_selection_flag` is set based on whether `edge_5s_after < 0`. This requires maintaining a reference to the data feed's current state or querying the CLOB `/midpoint` endpoint at T+5s and T+10s.

### 6.8 Wallet management (`wallet.py`)

**Responsibility:** Handle Polygon wallet operations for Polymarket trading.

**V1 operations:**
- **Balance check:** Query USDC.e balance on Polygon before session start
- **Token split:** Split USDC.e into YES + NO pairs via Polymarket's CTF contract (needed to have sell-side inventory)
- **Token merge:** Merge YES + NO pairs back to USDC.e after session (recover capital)
- **Order signing:** EIP-712 signature for CLOB orders using `eth_account` library
- **Token redemption:** After market resolution, redeem winning tokens for USDC

**CTF contract addresses:** The split, merge, and redeem operations require interaction with Polymarket's Conditional Token Framework contracts on Polygon. Contract addresses are documented at `https://docs.polymarket.com/resources/contract-addresses` and should be stored in `constants.py`.

**Security:** Private key is loaded from environment variable, never logged or written to DB. The `config_snapshot` JSONB field in `pm.sessions` explicitly excludes the private key.

### 6.9 Fee model (`fee_model.py`)

**Responsibility:** Compute Polymarket fees for analysis and threshold decisions.

**Fee formula (from Polymarket docs):**
```
taker_fee = C × p × feeRate × (p × (1 - p))^exponent
```

**Two regimes tracked:**
- Pre-March 30, 2026: `feeRate=0.25`, `exponent=2` (peak ~1.56% at p=0.50)
- Post-March 30, 2026: `feeRate=0.072`, `exponent=1` (peak ~1.80% at p=0.50)

**V1 usage:** The fee model is used for PnL attribution (decompose fills into spread capture vs fee cost) and for logging. It is not used to dynamically adjust quoting in V1 — that's a Phase 2 optimization.

**Maker rebate estimation:** `rebate_pool = 0.20 × taker_fee_pool_for_market`. Per-maker share depends on your fraction of fee-equivalent executed liquidity. Recorded for analysis but not used for quoting decisions in V1.

---

## 7. API integration

### 7.1 New API routers

Add a new router `services/api/routers/polymarket.py` with endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/v1/polymarket/sessions` | GET | List recent trading sessions with PnL summary |
| `/v1/polymarket/sessions/{session_id}` | GET | Detailed session view (config, PnL decomposition, fills, order count) |
| `/v1/polymarket/sessions/active` | GET | Get currently active session (if any) |
| `/v1/polymarket/fills` | GET | List fills across sessions (filterable by date range) |
| `/v1/polymarket/pnl/summary` | GET | Aggregate PnL across all sessions (total, average per session, cumulative curve) |
| `/v1/polymarket/health` | GET | Service health (last session status, wallet balance, next scheduled window) |

### 7.2 Shared schemas

Add `packages/common/polymarket_schemas.py` with Pydantic response models consumed by the API and dashboard:

- `PMSessionSummary` — session list item (id, window, PnL, status, fill count)
- `PMSessionDetail` — full session with config, PnL decomposition, order/fill counts
- `PMFillRecord` — individual fill for the fills list
- `PMPnLSummary` — aggregate PnL with cumulative curve data
- `PMHealthStatus` — service health for the health endpoint

---

## 8. Dashboard integration (future — Phase 2+)

Not built in V1, but the API endpoints above provide the data contract. The dashboard page would show:

- **Session history table:** Date, window, PnL, fills, status — one row per day
- **Cumulative PnL chart:** Running total across sessions
- **Live session panel** (when active): Current mid, spread, inventory, unrealized PnL, time remaining
- **PnL decomposition:** Stacked bar chart breaking out spread capture, inventory drift, rebates, rewards per session

This follows existing dashboard patterns (SWR polling, Shadcn/UI tables, Recharts) and would live at a route like `/(dashboard)/polymarket/`.

---

## 9. Prerequisites — account and wallet setup

This section must be completed manually before the bot can run.

### 9.1 Polymarket account

1. Create a Polymarket account at polymarket.com (or polymarket.us if US-based).
2. Verify identity if required by the platform.
3. Note the API access model — Polymarket uses wallet-based authentication, not API keys. Your wallet IS your identity.

### 9.2 Polygon wallet

1. Generate a new Ethereum-compatible wallet (dedicated to bot trading — do not reuse a personal wallet).
2. Store the private key securely. It will be provided to the bot via environment variable.
3. Fund the wallet with a small amount of MATIC on Polygon (for gas fees on token operations like split/merge/redeem). ~$1-2 of MATIC is sufficient for weeks of operation.
4. Fund the wallet with USDC.e on Polygon. For dust-capital phase: $50-100.
   - Bridge from Ethereum mainnet, or purchase directly on Polygon via an exchange that supports Polygon withdrawals.

### 9.3 Environment configuration

Add to `configs/environments/.env.polymarket`:
```
PM_PRIVATE_KEY=<wallet-private-key>
PM_WALLET_ADDRESS=<wallet-public-address>
PM_TARGET_HOUR_UTC=13
PM_DATABASE_URL=postgresql://...
```

### 9.4 Polymarket API access

- **Public endpoints** (Gamma, Data, CLOB orderbook): No authentication needed.
- **Trading endpoints** (place order, cancel, heartbeat): Authenticated via EIP-712 signed messages using your wallet. No separate API key provisioning needed — the SDK handles signing.
- **Rate limits:** Documented per-endpoint. The bot must implement adaptive pacing. Key limits: CLOB trading has burst (up to 50 req/s depending on endpoint) and sustained limits.

### 9.5 Dependency: py-clob-client

Polymarket provides an official Python SDK: `py-clob-client`. This handles:
- Order construction and EIP-712 signing
- REST API calls with proper authentication headers
- WebSocket connection management

Install via: `pip install py-clob-client`

---

## 10. Future roadmap — Phase 2 and Phase 3

Everything in this section is documented for future implementation. It captures all research findings and design decisions that are not part of V1.

### 10.1 Phase 2: Advanced market making

**Inventory skew (Avellaneda-Stoikov):**
Shift the quoting center based on current inventory to mean-revert toward flat:
```
center = midpoint - φ × inventory
```
Where `φ` is an inventory aversion parameter tuned from Phase 1 data. When long YES, the center shifts down (more aggressive selling, less aggressive buying).

**Dynamic spread:**
Adjust spread based on:
- **Realized volatility:** Wider spread when BTC is volatile (protects against adverse selection)
- **Time-to-close:** Widen in the last 10-15 minutes as toxic flow increases
- **Orderbook depth:** Tighten when deep book, widen when thin
- **Spread formula:** `δ(t) = δ_base + α × σ(t) + β × max(0, 1 - time_remaining/T_threshold)`

**Fee-aware quoting thresholds:**
Don't place quotes where expected spread capture minus fee cost is negative. The minimum profitable spread depends on the fee curve:
```
min_edge = spread/2 + slippage + fee_edge(p, C) + model_risk_buffer
```
Skip quoting when `midpoint` is in the fee deadzone near 0.50 (where taker fees peak).

**Reward tracking and optimization:**
- Query rewards endpoints for `rewards_max_spread` and `rewards_min_size` per market
- Verify order scoring status via `GET /order-scoring` endpoint (already in CLOB client from V1, used for logging; Phase 2 uses it for active optimization)
- Ensure quotes stay within reward eligibility bounds when a market has active liquidity rewards
- Track daily reward/rebate payouts via Data API activity types (`REWARD`, `MAKER_REBATE`)
- Add `pm.daily_payouts` table to store daily payout records and attribute them back to sessions

**PnL decomposition pipeline:**
Break session PnL into:
- **Spread capture:** Σ ε_k × C_k × (p_k - m_t_k) for each fill
- **Inventory drift:** ∫ q_t dm_t + q_T × (Y - m_T) at settlement
- **Maker rebates:** From Data API rebates endpoint
- **Liquidity rewards:** From Data API activity endpoint
- **Operational costs:** Gas fees for split/merge/redeem

**Session wind-down optimization:**
Use Phase 1 data to determine optimal wind-down timing. Analyze last-N-minute fill toxicity (fraction of fills that go against you) to find the crossover point where quoting becomes negative EV.

**High-leverage Phase 2 optimizations:**

1. **Quote stickiness analysis:** Compute metrics from `quote_version_id` and `time_on_book_seconds`:
   - Average requote frequency
   - Correlation between cancel frequency and adverse selection
   - Optimal requote interval by regime
   - Queue position decay rate (how fast you lose priority when not refreshing)

2. **Fill probability vs distance curve:** Use `(price - midpoint_at_place)` from orders and fill outcomes to build a logistic regression:
   ```
   P(fill | distance, regime) = logistic(β₀ + β₁ × distance + β₂ × volume_regime + ...)
   ```
   This becomes the core model for dynamic spread optimization — quote at the distance that maximizes `expected_fill_rate × spread_capture - adverse_selection_cost`.

3. **Toxic flow curve by minute:** Use `pm.toxic_flow_by_minute` to build an empirical curve of `adverse_fill_pct(t)` over the hour. Fit a functional form (e.g., exponential increase near close) and use it to dynamically widen spread or reduce size in the danger zone.

4. **Regime-specific strategy:** Use session regime tags to build separate parameter sets:
   - HIGH volatility → wider spread, smaller size
   - TIGHT spread regime → more aggressive quoting (competition is lower)
   - LOW volume → skip session or quote very conservatively

### 10.2 Phase 3: Hybrid strategy (directional model layer)

**Probability model:**
Train a model to estimate P(Up | intra-hour price path, market state) in real time.

**Feature set (from research):**
- **Price-path features (Binance):** distance-to-open `d(t) = ln(P_t/O_h)`, realized volatility over 1m/5m/15m windows, momentum (rolling z-scores, sign persistence)
- **Perp funding/basis (Binance futures):** `lastFundingRate`, `markPrice - indexPrice` as sentiment/carry proxies
- **Polymarket microstructure:** implied probability series, spread, orderbook imbalance, time since last trade, tick-size regime
- **Time features:** time-to-close, hour-of-day, day-of-week

**Model candidates:**
| Model | Strengths | Use when |
|---|---|---|
| Logistic regression / GLM | Interpretable, fast, robust baseline | First model; easy to add interactions (time-to-close × distance-to-open) |
| Time-series GLM (lagged) | Captures microstructure lag explicitly | Lead-lag testing against Polymarket implied probability |
| LSTM | Nonlinear temporal patterns | After GLM baseline is established and more data collected |
| Transformer | Long-range dependencies, multi-modal input | Future research; heavy compute |

**Calibration:**
- Brier score and log loss as primary metrics (proper scoring rules)
- Reliability diagrams for calibration diagnostics
- Platt scaling or isotonic regression for post-hoc calibration
- Walk-forward cross-validation (never mix future data into training)

**Lead-lag testing:**
Test whether the model's probability estimate leads Polymarket's implied probability:
```
Δp_PM(t+τ) = α + β × (p_hat(t) - p_PM(t)) + γ × Δp_PM(t) + ε_t
```
If β > 0 for small τ (10s-300s), the model has predictive lead. Use cross-correlation, Granger causality, and event studies near close.

**Quoting integration:**
When the model is confident, skew the quoting center:
```
center = midpoint - φ × inventory - ψ × (p_hat - p_PM)
```
Where `ψ` controls how aggressively directional signal affects quoting.

**Actionable decision threshold:**
Only act on model signal when mispricing exceeds frictions:
```
|M(t)| >= spread/2 + slippage(C) + fee_edge(p, C) + model_risk_buffer
```

### 10.3 Phase 2+: Dynamic window selection

**Reward-density ranking pipeline (from research):**
For each candidate hourly window, compute:
```
Score_i = E[Incentives_i] / (Competition_i^α × Risk_i^β)
```

Where:
- `E[Incentives_i]` = maker_rebate_pool × expected_share + liquidity_reward_pool × expected_share
- `Competition_i` = 1/HHI from on-chain OrderFilled maker shares (effective number of makers)
- `Risk_i` = z(σ_i) + λ × z(toxicity_i) from Binance volatility + last-5-min flow imbalance

**Data sources for ranking:**
- Gamma API for market discovery and metadata
- Data API trades endpoint for volume + last-minute toxicity
- CLOB `/fee-rate` for fee enablement
- On-chain `OrderFilled` events for maker concentration (HHI)
- Binance 1H klines for volatility
- Rewards endpoints for pool sizes and eligibility constraints

**The goal:** Replace the fixed window with a daily pre-session ranking step that selects the highest reward-density window.

### 10.4 Future: Multi-window and 5m/15m markets

**Multi-window quoting:** Run across 2-3 hourly windows per day to increase data collection and diversify. Requires managing capital across concurrent sessions and handling overlapping markets.

**Shorter-duration markets (5m, 15m):** These use Chainlink data streams instead of Binance candles. The model would need different features and potentially faster requoting. Higher throughput but also higher competition and more toxic flow.

### 10.5 Future: Dashboard deep integration

- **Real-time session view:** WebSocket-fed live panel showing current mid, spread, inventory, PnL, time remaining
- **PnL decomposition charts:** Stacked area chart showing spread capture vs inventory drift vs rebates over time within a session
- **Session comparison:** Side-by-side comparison of sessions with different parameters
- **Parameter tuning UI:** Adjust spread, inventory cap, wind-down time from the dashboard and see historical performance at different parameter values
- **Unified portfolio view:** Show Polymarket PnL alongside equity PnL in the main dashboard overview

### 10.6 Future: Competition analysis

- Track maker concentration over time via on-chain OrderFilled events
- Compute effective number of makers (HHI) per market window
- Monitor leaderboard data for competitor profiling
- Detect regime changes in competition (new entrants, departures)

### 10.7 Future: Cloud deployment

When the bot proves profitable with dust capital and graduates to meaningful capital:
- Move to a lightweight cloud VM (e.g., DigitalOcean droplet, $5-10/month)
- Add as a container to docker-compose or deploy standalone
- Implement proper secret management (cloud secret store instead of env file)
- Add monitoring/alerting (SMS/Slack on session errors, heartbeat failures)
- Add auto-restart and crash recovery

---

## 11. Risks and mitigations

### Financial risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Adverse selection near close | Fills go against you as candle outcome becomes predictable | High | Wind-down at T+55min; widen spread near close (Phase 2) |
| Inventory stuck at resolution | Holding wrong-side tokens at binary settlement | Medium | Inventory cap; merge before resolution if possible |
| Fee regime change | March 30 update changes economics | Certain | Fee model supports both regimes; recalibrate after change |
| Competition increases | More makers compress spread capture | Medium | Monitor via on-chain data; shift to less competitive windows |
| Platform risk | Polymarket changes rules, APIs, or fee structure | Low-Medium | Modular adapter layer; monitor changelog |

### Operational risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Heartbeat failure | All orders cancelled unexpectedly | Medium | 5s heartbeat cadence; reconnect logic; cancel-all is fail-safe |
| WebSocket disconnect | Stale orderbook → bad quotes | Medium | Cancel all on disconnect; don't quote until book is fresh |
| Rate limiting | Delayed cancels/requotes in fast market | Medium | Adaptive pacing; jittered backoff; conservative requote frequency |
| Weekly engine restart | Orders rejected during restart | Certain (weekly) | Detect HTTP 425; pause and retry; verify current restart schedule in Polymarket docs/changelog before selecting target window (docs show Tuesdays 7AM ET, but this may change) |
| Private key compromise | Wallet funds stolen | Low | Dedicated bot wallet; minimal balance; never log key |
| Local machine goes offline | Session interrupted mid-hour | Medium | Heartbeat auto-cancels orders (fail-safe); session recovery on restart |

### Regulatory risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Geo-restriction | Orders rejected from blocked region | Low | Verify eligibility; Polymarket US vs international distinction |
| Platform terms violation | Account restricted | Low | Stay within documented API usage; no manipulation or wash trading |
| Regulatory change | Product delisted or restricted | Low-Medium | Monitor CFTC/regulatory news; modular design allows pivoting |

---

## 12. Build sequence (V1 tickets)

Suggested ticket ordering for implementation. Each ticket is one bounded unit of work.

| # | Ticket | Dependencies | Scope |
|---|---|---|---|
| 1 | **Project scaffolding** | None | Create `services/polymarket/` directory structure, `pyproject.toml`, config module, constants |
| 2 | **Polymarket adapter: Gamma client** | #1 | Implement `gamma_client.py` — market discovery, metadata fetch |
| 3 | **Polymarket adapter: CLOB client** | #1 | Implement `clob_client.py` — REST (orders, cancel, cancel-all, heartbeat, book, fee-rate, order-scoring) + WebSocket (market channel) |
| 4 | **Polymarket adapter: Binance client** | #1 | Implement `binance_client.py` — 1H klines, current price |
| 5 | **Wallet management** | #1 | Implement `wallet.py` — balance check, order signing, split/merge, redeem |
| 6 | **Data model and migrations** | #1 | Create `pm.*` tables in TimescaleDB via Alembic migration (in `services/data/` alongside existing migrations for shared migration history) |
| 7 | **Market discovery** | #2, #6 | Implement `market_discovery.py` — find target market, write metadata |
| 8 | **Data feed** | #3, #4 | Implement `data_feed.py` — WebSocket book tracking + Binance price, derived state |
| 9 | **Recorder** | #6 | Implement `recorder.py` — async writes for snapshots, orders, fills, PnL, sessions |
| 10 | **Fee model** | #1 | Implement `fee_model.py` — fee computation for both regimes, rebate estimation |
| 11 | **Safety layer** | #3 | Implement `safety.py` — cancel-all, inventory cap, session loss limit, wind-down timer |
| 12 | **Quoting engine** | #8 | Implement `quoting_engine.py` — V1 fixed symmetric spread around midpoint |
| 13 | **Executor** | #3, #5, #12, #11 | Implement `executor.py` — order placement loop, heartbeat loop, cancel/replace |
| 14 | **Session orchestrator** | #5, #7, #8, #9, #10, #11, #12, #13 | Implement `session.py` — full session lifecycle (pre-session → active → wind-down → post) |
| 15 | **Main entry point and scheduler** | #14 | Implement `main.py` — CLI entry point, pre-session wake-up, session launch |
| 16 | **Shared schemas** | #6 | Create `packages/common/polymarket_schemas.py` — API response models |
| 17 | **API routers** | #16 | Add `services/api/routers/polymarket.py` — session list, detail, fills, PnL summary, health |
| 18 | **Polymarket adapter: Data API client** | #1 | Implement `data_api_client.py` — trades, activity, rebates (V1: fill verification and diagnostics; Phase 2: reward attribution) |
| 19 | **Integration test: dry-run session** | #15 | End-to-end test: discover market, connect feeds, run quoting loop with no capital, verify data recording |
| 20 | **Prerequisites documentation** | None (can be parallel) | Write setup guide: wallet creation, funding, env config, dependency install |

---

## 13. Glossary

| Term | Definition |
|---|---|
| **Condition ID** | Polymarket's unique identifier for a market (maps to an on-chain condition) |
| **Token ID** | ERC-1155 token identifier for a specific outcome (YES or NO) |
| **CLOB** | Central Limit Order Book — Polymarket's off-chain matching engine |
| **Post-only** | Order type that is rejected if it would immediately match (guarantees maker status) |
| **GTC** | Good-til-cancelled — order stays on book until filled or cancelled |
| **Heartbeat** | Periodic ping to Polymarket to maintain order liveness (~10s timeout) |
| **Mid / Midpoint** | (best_bid + best_ask) / 2 — the implied probability |
| **Spread** | best_ask - best_bid |
| **Inventory** | Net position in YES (or NO) tokens |
| **Inventory skew** | Shifting quote center based on inventory to mean-revert toward flat |
| **Maker rebate** | USDC paid daily to makers whose resting orders were taken; 20% of taker fees for crypto |
| **Liquidity reward** | Separate daily USDC reward for providing quality quotes (tight spread, sufficient size) |
| **Wind-down** | Period at end of session where bot cancels quotes to avoid toxic last-minute flow |
| **Fee-equivalent** | Notional value used to compute maker rebate share (same formula as taker fee) |
| **Distance-to-open** | ln(current_BTC_price / hour_open_BTC_price) — key signal for directional model |
| **Toxic flow** | Informed taker orders that adversely select stale maker quotes, especially near close |
| **HHI** | Herfindahl-Hirschman Index — measure of maker concentration in a market |
| **Reward density** | Expected incentive income per unit of competition and risk — ranking metric for window selection |
