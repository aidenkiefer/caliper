# UI Data Audit (Dashboard)

Applies to `apps/dashboard` pages **except** Getting Started and Platform (excluded by request).

## Where work is tracked (source of truth)

- Primary tracker: this doc (`docs/ui-data-audit.md`) for “is this UI real data yet?”
- Implementation work items (tickets): `docs/plans/tickets/17-*` (the “no dummy data” push)
- Supporting design docs:
  - Runtime paper MTM: `docs/system-design/runtime-paper-portfolio.md`
  - Recommendations taxonomy: `docs/system-design/recommendations.md`

## Demo mode vs real mode

The dashboard now supports an explicit demo mode:

- `NEXT_PUBLIC_DEMO_MODE=true`: UI will use demo fallback data when the API is unavailable.
- (default) `NEXT_PUBLIC_DEMO_MODE` unset/false: UI will **not** silently show fake data. Pages render empty/“backend unavailable” states instead.

The dashboard API base is controlled by:

- `NEXT_PUBLIC_API_URL` (expected shape: `http(s)://host:port/v1`)

Backend DB URL note (paper MTM work):
- The backend now treats `DATABASE_URL` as canonical, with `DB_URL` as a fallback for asyncpg paths. If both are set and differ, the backend should warn/fail to avoid environment drift.

## Page-by-page audit

## “No dummy data” tracker (recommended source of truth)

This doc is the primary place to track whether each UI surface is backed by **real** API data vs demo/mock/stub.

Completed:
- ✅ Runtime paper MTM metrics + snapshots (`/v1/metrics/summary` + `paper.equity_snapshots`)
- ✅ Strategies list/detail no longer mock-backed (derived from paper activity; performance fields optional)
- ✅ Runs endpoint no longer serves mock runs (returns empty / 501 instead of fake objects)
- ✅ Health endpoint no longer reports fake “healthy” (real DB ping; others degraded until wired)
- ✅ Fleet/Ranking no longer serve mock JSON; paper trades are DB-backed; fleet status/signals are persisted when orchestrator runs; ranking is DB-computed
- ✅ Alerts are DB-backed (`paper.alerts`; migration `012_create_paper_alerts.py`)
- ✅ Recommendations queue/decisions are DB-backed (`ml.recommendations`; migration `013_create_recommendations_table.py`)

Remaining (no dummy data):
- 🚧 Alerts: emit from real sources (risk + feed health + drawdown warnings)
- 🚧 Recommendations: producer pipeline TBD (queue is persisted; generation still not wired)
- 🚧 Simulation/Evaluation/Probability: wire to real persisted outputs (API now returns 501 instead of stub payloads)
- 🚧 Settings: decide client-only vs server-backed; avoid placeholder UIs implying persistence

### Overview (`/`)

UI widgets:
- Portfolio summary cards + equity curve: `GET /v1/metrics/summary`
- Alerts widget: `GET /v1/alerts`, `PATCH /v1/alerts/{alert_id}/acknowledge`
- Sprint 16 Fleet Control: `GET /v1/ranking/current`, `GET /v1/fleet/status`, `GET /v1/fleet/signals`

Backend status:
- `GET /v1/metrics/summary` is now computed from the **runtime paper portfolio layer** (paper-first MTM):
  - allocations: `paper.allocations` (paper capital allocated per bot/strategy)
  - fills:
    - Polymarket: `pm.paper_trades` (paper fills from the fleet/orchestrator)
    - Equities: `paper.equity_fills` (strategy-attributed equity fills)
  - marks:
    - Polymarket: `pm.orderbook_snapshots` (midpoint when spread ≤ 0.05, else last trade price)
    - Equities: currently falls back to last fill price (until wired to broker quote path)
  - equity curve source: `paper.equity_snapshots` (stable charting; `strategy_id = NULL` is portfolio aggregate)
- Alerts endpoints are DB-backed (`paper.alerts`; migration `012_create_paper_alerts.py`).
  - Initial emitters (Phase 1 operational + safety) are triggered opportunistically by `GET /v1/metrics/summary` and `POST /v1/controls/kill-switch`:
    - data feed staleness (Polymarket orderbook + equities price bars)
    - kill switch activate/deactivate
    - drawdown warning/halt thresholds (daily + total)
    - fleet heartbeat delayed/missed
- Fleet + ranking endpoints exist.
  - `GET /v1/fleet/paper-trades` is **DB-backed** from `pm.paper_trades` and returns the raw trade fields (no fabricated P&L).
  - `GET /v1/fleet/status` is backed by `pm.fleet_status_snapshots` (written by the fleet orchestrator when running).
  - `GET /v1/fleet/signals` is backed by `pm.fleet_signals` (written by the fleet orchestrator when running).
  - `GET /v1/ranking/current` is computed from live DB state (`pm.sessions` + latest `pm.orderbook_snapshots`) and also writes best-effort snapshots to `pm.ranked_universe_snapshots` for debugging/stability.

Backend TODOs to make “real”:
- Phase 1 improvements:
  - Wire equity marks to the canonical broker/runtime quote path (to replace the “last fill price” fallback).
  - Optional: add a periodic snapshot job (right now snapshots are triggered on allocation/fill events).
  - Emit alerts from risk + data-feed health + drawdown warnings (alerts are now DB-backed; emitters remain).
- Phase 2 (live) replacement:
  - Replace paper-ledger metrics with broker/wallet equity + positions + fills + mark-to-market.
- Emit and persist alerts from:
  - risk layer (kill switch/circuit breaker triggers)
  - data feed health (staleness/disconnects)
  - portfolio drawdown threshold warnings

### Strategies (`/strategies`, `/strategies/[id]`)

UI widgets:
- Strategy fleet table: `GET /v1/strategies` (expects performance summary columns)
- Strategy detail header + KPI cards: `GET /v1/strategies/{strategy_id}`
- Positions tab: `GET /v1/strategies/{strategy_id}/positions` (derived from runtime paper fills; includes mark + unrealized P&L)
- Paper allocation UI: `POST /v1/paper/allocations`
- Equities fill ingest (Phase 1 wiring tool): `POST /v1/paper/equity-fills`
- Explanations tab (currently hardcoded UI): should use `GET /v1/explanations?strategy_id=...`
- Logs tab (currently hardcoded UI): needs an activity/event source (OMS events, strategy events, etc.)

Backend status:
- Strategy list/detail endpoints now derive strategy IDs from **real runtime paper activity** (allocations/fills) and return minimal metadata (`services/api/routers/strategies.py`).
- Performance summary fields on strategy list/detail remain optional; the dashboard displays `—` when not available (preferred over fake zeros).
- Runtime sleeve endpoints exist for live paper MTM surfaces:
  - `GET /v1/strategies/{id}/sleeve`
  - `GET /v1/strategies/{id}/positions`
  - `GET /v1/strategies/{id}/fills`
- The dashboard now includes:
  - allocate-capital UI on `/strategies` and `/strategies/[id]`
  - a “record equities fill” tool on `/strategies/[id]` for wiring honest MTM from fills

Backend TODOs to make “real”:
- Persist strategy configs and lifecycle status (DB table + CRUD).
- Compute and attach performance summaries per strategy (from run history or from live/paper PnL attribution).
  - For equities: replace manual `paper.equity_fills` ingest with fills captured automatically from the equities execution layer.

### Runs (`/runs`, `/runs/[id]`)

UI widgets:
- Run history: `GET /v1/runs`
- Run detail report: `GET /v1/runs/{run_id}`
- New Backtest button: `POST /v1/runs` (currently UI-only; needs wiring + async job status)

Backend status:
- Runs endpoints exist but are not yet wired to the real backtest/persistence layer. The API no longer serves mock runs (`services/api/routers/runs.py` currently returns an empty list + 501 for creation).
- Run detail schema was expanded to match UI expectations (run metadata + equity curve + trades).

Backend TODOs to make “real”:
- Persist runs, metrics, equity curves, and trades (DB tables).
- Wire `POST /v1/runs` to the real backtest engine/job queue and update status over time.
- Produce a durable “report artifact” (HTML/JSON) and store a `report_url` if desired.

### Models (`/models`, `/models/[id]`)

UI widgets:
- Model list: `GET /v1/models`
- Model detail: `GET /v1/models/{model_id}`
- Lifecycle controls: `PATCH /v1/models/{model_id}`
- Performance: `GET /v1/metrics/performance/{model_id}`
- Drift/health: `GET /v1/drift/metrics/{model_id}`, `GET /v1/drift/health/{model_id}`

Backend status:
- `GET/PATCH /v1/models...` were added (`services/api/routers/models.py`) and discover models from `MODEL_REGISTRY_DIR` joblib artifacts.
- Drift and baselines endpoints had a route-prefix bug fixed (they now mount under `/v1/drift/...` and `/v1/baselines/...` as intended).
- Drift/performance currently depend on in-memory stores unless wired to persisted metrics.

Backend TODOs to make “real”:
- Persist model metadata + lifecycle state in DB (instead of in-memory).
- Store rolling performance/drift metrics and expose them through the API.

### Recommendations (`/recommendations`)

UI widgets:
- Approval queue: `GET /v1/recommendations`
- Approve/reject: `POST /v1/recommendations/{id}/approve`, `POST /v1/recommendations/{id}/reject`
- Stats: `GET /v1/recommendations/stats?strategy_id=...` (UI currently shows placeholders for totals/rate)

Backend status:
- Endpoints exist and are DB-backed (`ml.recommendations`; migration `013_create_recommendations_table.py`).
- UI fetches the queue from the API (no hardcoded recommendations).

Backend TODOs to make “real”:
- Produce recommendations from actual model inference output, and link to explanations (`/v1/explanations/...`).

Design clarification (current direction):
- Recommendations should cover **two distinct kinds**:
  - **Action recommendations** (runtime): trade/order intents that require HITL approval and still must pass risk controls.
  - **Strategy tuning recommendations** (optimization): suggested parameter/config changes or experiments to improve bot performance over time.
- Proposed design notes: `docs/system-design/recommendations.md`.

### Health (`/health`)

UI widgets:
- Health grid: `GET /v1/health`
- Rate limits section: currently hardcoded UI

Backend status:
- Endpoint exists and now performs a **real DB ping** for the `database` service; other services are reported as `degraded` until wired to real probes (`services/api/routers/health.py`).

Backend TODOs to make “real”:
- Wire database ping, redis ping, broker connectivity, data feed staleness, and risk manager state into the health endpoint.
- Expose rate limit telemetry via API (or remove the hardcoded panel).

### Settings (`/settings`)

UI status:
- Mostly static placeholders (no real persistence; not backed by API).

Backend TODOs to make “real”:
- Decide what settings are “client-only” (localStorage) vs server-backed (user profile, alert prefs, API config).

### Help (`/help`)

UI status:
- Fully functional local glossary/search (no backend required).
