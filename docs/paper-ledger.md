# Paper Ledger (Phase 1 Source of Truth)

During Phase 1 (paper trading / sandbox), portfolio equity and P&L are computed from an **append-only paper ledger** rather than any broker account.

This supports your goal of allocating “paper funds” to bots (e.g., `$100/week/bot`) and tracking each bot’s performance over time, while keeping the dashboard honest and deterministic.

## Data model

Postgres schema: `paper`

Tables:
- `paper.allocations`: paper USD allocated to a `strategy_id` over time
- `paper.pnl_events`: P&L deltas attributed to a `strategy_id` over time (positive or negative)

Migration:
- `services/data/alembic/versions/008_create_paper_ledger_tables.py`

## API

Ledger write endpoints:
- `POST /v1/paper/allocations`
- `POST /v1/paper/pnl-events`

Ledger read endpoint:
- `GET /v1/paper/ledger`

Portfolio KPI endpoint (computed from runtime paper portfolio state, with stable history from snapshots):
- `GET /v1/metrics/summary?period=...&mode=PAPER`

## How metrics are computed (current)

`/v1/metrics/summary` computes portfolio KPIs from:
- `paper.allocations` (starting capital per sleeve)
- fill streams (Polymarket `pm.paper_trades`, equities `paper.equity_fills`)
- MTM marks (Polymarket `pm.orderbook_snapshots`, equities quote path)
- stable equity curve from `paper.equity_snapshots` (portfolio aggregate rows have `strategy_id = NULL`)

The following fields may be placeholders depending on mark availability and fill ingestion:
- `win_rate` (requires win/loss attribution)

## Phase 2 (live) plan

When switching to real capital:
- keep the **same UI contract** (`GET /v1/metrics/summary`), but swap the implementation to compute from:
  - broker/wallet equity
  - positions
  - fills
  - mark-to-market pricing
- keep the paper ledger for historical sandbox runs and backtesting comparisons
