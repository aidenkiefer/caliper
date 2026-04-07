# Runtime Paper Portfolio — Lightweight Implementation Plan

Status: Proposed  
Last updated: 2026-04-06

This plan implements the Phase 1 runtime paper portfolio design in a minimal, end-to-end way, prioritizing correctness and dashboard honesty.

## 0) Prereqs / invariants

- Canonical DB env var: `DATABASE_URL`
- `DB_URL` permitted only as fallback; warn loudly or fail if both are set and differ.

## 1) Schema migrations

1. Add `paper.equity_fills` (equities paper fills; strategy-attributed).
2. Add `paper.equity_snapshots` (per-strategy + portfolio snapshots, where `strategy_id IS NULL` is the portfolio row).
3. Extend `pm.orderbook_snapshots` with `last_trade_price` so the dashboard API can apply mark rules without depending on in-process feed state.

Deliverable:
- New Alembic migrations under `services/data/alembic/versions/`.

## 2) DB URL standardization

1. Update asyncpg users (fleet + polymarket services) to read `DATABASE_URL` first, and only fall back to `DB_URL`.
2. Add a shared helper for “resolve DB url + validate equality” to prevent drift.
3. Update `services/api/routers/fleet.py` gating to use the standardized DB URL.

Deliverable:
- A single reliable DB target across all runtime services.

## 3) Portfolio aggregation module

Add a small aggregation module (e.g. `services/portfolio/paper_portfolio.py`) that exposes:

- `compute_strategy_sleeve(strategy_id, as_of=now)`:
  - reads allocations
  - reads fills per surface (`pm.paper_trades`, `paper.equity_fills`)
  - derives avg-cost positions
  - pulls marks (Polymarket from `pm.orderbook_snapshots`, equities from broker/quote path)
  - returns sleeve metrics + derived positions

- `compute_portfolio(as_of=now)`:
  - aggregates across all strategies with any allocations/fills
  - returns portfolio totals + per-strategy rollup

- `write_equity_snapshots(...)`:
  - writes `paper.equity_snapshots` rows for:
    - each strategy updated
    - the portfolio aggregate (`strategy_id NULL`)

Deliverable:
- One codepath used by both `/v1/metrics/summary` and strategy-level endpoints.

## 4) API endpoints

### Ingestion

- `POST /v1/paper/equity-fills`
  - insert into `paper.equity_fills`
  - compute + write snapshots for the affected strategy + portfolio

### Strategy runtime state

- `GET /v1/strategies/{strategy_id}/sleeve`
- `GET /v1/strategies/{strategy_id}/positions`
- `GET /v1/strategies/{strategy_id}/fills` (unified list)

### Portfolio KPIs

- Rewrite `GET /v1/metrics/summary` to:
  - compute latest portfolio metrics via aggregator
  - read equity curve from `paper.equity_snapshots` (stable)
  - opportunistically write a fresh snapshot if stale/missing

Deliverable:
- Honest backend endpoints that reflect runtime paper MTM state.

## 5) Dashboard wiring

1. Keep `NEXT_PUBLIC_DEMO_MODE` behavior (demo-only fake data).
2. Update Overview to fully rely on `/v1/metrics/summary` for:
   - KPI cards
   - equity curve
3. Update Strategy detail to display:
   - sleeve metrics (`/v1/strategies/{id}/sleeve`)
   - derived positions (`/v1/strategies/{id}/positions`)
   - unified fills (`/v1/strategies/{id}/fills`)

Deliverable:
- UI surfaces consistently show real data when the backend is available.

## 6) Follow-ups (optional / Phase 1.5)

- Add a small periodic snapshot worker (e.g., every 30–60s) to keep curves fresh without relying on user traffic.
- Add a UI “Allocate capital” action that calls `POST /v1/paper/allocations` and triggers snapshots.
- Add alert emission based on sleeve drawdown / mark staleness / data feed health.

