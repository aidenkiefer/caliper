# Runtime Paper Portfolio (Phase 1) — System Design

Status: Draft (approved direction)  
Last updated: 2026-04-06

## Summary

We will make the dashboard’s portfolio equity/P&L **honest** by deriving it from a **runtime paper portfolio state** (cash + open positions marked-to-market), with **per-strategy sleeves** (mini funds) as the organizing model.

The simulation/backtest engines remain **secondary/offline** sources for evaluation and attribution only.

## Goals

1. Provide a single, consistent source of truth for Phase 1 “paper trading” portfolio metrics:
   - portfolio equity curve and KPIs (Overview page)
   - per-strategy sleeve metrics and positions (Strategies pages)
2. Support **mixed surfaces** in Phase 1:
   - Polymarket paper trading (existing `pm.*` persistence)
   - Equities paper trading (to be added as `paper.equity_fills`)
3. Preserve the “capital allocator” model:
   - allocations are **additive contributions** into a sleeve (no weekly resets)
   - weekly reporting is computed by time windows, not by resetting state
4. Keep the system minimal, correct, and extensible toward Phase 2 live trading.

## Non-goals (for this phase)

- Using the simulation engine as the runtime source of portfolio truth.
- Introducing a persisted `paper.positions` table (positions will be derived from fills).
- Persisting mutable per-strategy cash state (cash will be computed dynamically).
- Implementing Phase 2 live wallet/broker integration (we only preserve a clean swap-in path).

## Source-of-truth hierarchy

Phase 1 (paper):

1) **Paper capital allocation ledger**  
   `paper.allocations` (additive capital contributions)

2) **Runtime paper portfolio state** (derived from persisted fill streams)  
   - current cash (computed)
   - open positions (derived)
   - realized P&L (computed; avg-cost)

3) **Latest market marks**  
   - Polymarket: midpoint/spread/last-trade from canonical runtime feed (persisted for API consumption)
   - Equities: broker/runtime quote path

Simulation/backtest remains separate:
- offline evaluation/replay
- attribution and validation/debugging

## Portfolio model: “mini fund sleeve per strategy”

Each `strategy_id` is treated as its own sleeve.

Per strategy we expose:
- `starting_capital_usd` = Σ allocations
- `cash_usd` = starting_capital − buys_notional − fees + sells_notional
- `deployed_capital_usd` = cost basis of open positions (avg-cost)
- `equity_usd` = cash + Σ(position_qty × mark_price)
- `realized_pnl_usd` (avg-cost)
- `unrealized_pnl_usd` = Σ(open_position_mtm − open_position_cost_basis)

Portfolio aggregate:
- sum of all sleeves only (no unallocated cash bucket in Phase 1)

## Accounting method

- Use **average cost** (not FIFO) for realized/unrealized P&L computation.
- This is sufficient for Phase 1 and keeps cross-surface logic consistent.

## Mark-to-market (MTM) mark rules

### Polymarket

Canonical mark should reuse the existing runtime feed notion of midpoint/spread and last trade:

- If `spread <= 0.05` and midpoint exists: **use midpoint**
- Else: fallback to **market last trade**

Important: “last trade” should be the market’s last trade from the Polymarket feed, **not** our own paper fills.

To make this accessible to the dashboard API, we will persist `last_trade_price` alongside `midpoint`/`spread` in `pm.orderbook_snapshots`.

### Equities

- Use broker/runtime quote path (e.g., broker positions with `current_price` or a quote endpoint).

## Persistence strategy (Phase 1)

### Derived state (not persisted yet)

- `paper.positions` table: **not introduced** (positions derived from fills)
- per-strategy cash state: **not persisted** (computed dynamically)

### Persisted for stability and debugging

We will persist **equity snapshots** early.

- `paper.equity_snapshots` is the canonical history for:
  - equity curves (stable charts)
  - debugging and cross-checking computations
- Convention:
  - `strategy_id = NULL` => portfolio aggregate snapshot
  - `strategy_id != NULL` => per-strategy sleeve snapshot

Snapshot triggers (initial):
- on allocation events
- on fill events
  - equities fills: via API ingestion endpoint
  - polymarket paper fills: via existing services writing to DB; snapshots can be refreshed opportunistically at read-time until we add a worker

## Storage model (minimal schema)

Existing:
- `paper.allocations`
- `pm.paper_trades` (Polymarket paper fills)
- `pm.orderbook_snapshots` (midpoint/spread; will extend to include `last_trade_price`)

To add:

1) `paper.equity_fills`  
   Strategy-attributed equities paper fills.

2) `paper.equity_snapshots`  
   Periodic snapshots for per-strategy and portfolio equity/cash/MTM state.

## API contract (minimal)

### Ingestion / accounting

- `POST /v1/paper/allocations` (existing)
- `GET /v1/paper/ledger` (existing)
- `POST /v1/paper/equity-fills` (new; equities fill ingestion)

### Strategy sleeve state

- `GET /v1/strategies/{strategy_id}/sleeve` (new)
- `GET /v1/strategies/{strategy_id}/positions` (new; derived)
- `GET /v1/strategies/{strategy_id}/fills` (new; unified across surfaces)

### Portfolio aggregation

- `GET /v1/metrics/summary?period=...&mode=PAPER`
  - returns portfolio KPIs + equity curve from `paper.equity_snapshots`
  - computed from the same aggregation layer used by the strategy endpoints

Optional (debug/ops):
- `POST /v1/paper/snapshots/compute` (force compute latest snapshots)

## Aggregation layer

Introduce a small portfolio aggregation module/service that:
- reads allocations + fill streams per surface
- derives positions (avg-cost)
- applies MTM marks (per-surface rules)
- produces per-strategy sleeve state + portfolio aggregate
- persists snapshots

Key architectural constraint:
- Keep per-surface storage “under the hood”
- Unify at the aggregation layer / API layer, not by forcing a single DB schema for all surfaces.

## Database configuration standardization

Current repo has both `DATABASE_URL` (sync SQLAlchemy) and `DB_URL` (asyncpg).

Decision:
- Canonical: `DATABASE_URL`
- `DB_URL` allowed only as a fallback
- Warn loudly or fail if both are set and differ

This prevents a class of drift bugs where:
- Polymarket/fleet writes to one DB
- API reads from a different DB

## Phase 2 (live) path

We keep the **same API contracts** but swap the data sources:
- allocations may become “capital contributions” / actual deposits
- fills come from live broker/wallet adapters
- marks come from live market data / broker quotes

The simulation engine remains separate for evaluation/attribution.

## Risks / open questions

- Equities strategy attribution requires a reliable equities fill ingestion path (cannot be inferred solely from broker account positions).
- Snapshot freshness for Polymarket fills is not event-driven initially (may require opportunistic refresh or a lightweight periodic worker).
- Definition of “deployed capital” may differ by surface; we will standardize on avg-cost open-position cost basis for now.

