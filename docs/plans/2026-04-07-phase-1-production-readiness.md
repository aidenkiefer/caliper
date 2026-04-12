# Phase 1 Production Readiness (Paper Fleet + Real Data)

**Date:** 2026-04-07  
**Goal:** Make Caliper “actually usable” in Phase 1: bots run in **paper mode**, write real data to Postgres/Timescale, and the Vercel dashboard shows that real data (no dummy data in production).

---

## 0) What “Production” Means for This Repo

Caliper has three distinct runtime responsibilities:

1. **Dashboard (Next.js)** — deployed on **Vercel**  
2. **API (FastAPI)** — deployed on **persistent compute** (VM/container platform)  
3. **Workers (long-running loops)** — deployed on **persistent compute** (VM/container platform)  

> Vercel is excellent for the dashboard, but it is not a good fit for long-running fleet loops. The fleet/recorders should run elsewhere and write into the same DB the API reads.

---

## 1) Minimum Phase 1 Service Set

### Required

- **Postgres + TimescaleDB** (managed or self-hosted)
- **FastAPI** (`services/api`) publicly reachable by the dashboard
- **Paper fleet worker** (long-running process) that writes:
  - `pm.paper_trades`
  - `pm.fleet_status_snapshots`
  - `pm.fleet_signals`
  - (optionally) periodic `paper.equity_snapshots` via API endpoints or direct portfolio calls

### Strongly recommended (Polymarket surface)

- **Polymarket recorder / data feed** (so MTM marks and ranking inputs exist):
  - `pm.orderbook_snapshots` (used for Polymarket marks and staleness alerts)
  - `pm.sessions` and `pm.market_metadata` (used by `/v1/ranking/current` candidates)

### Optional (today)

- **Redis** (`REDIS_URL`) — currently non-critical for Phase 1, but useful for queues later

---

## 2) Database (Timescale/Postgres) Setup

### 2.1 Choose a production DB provider

Requirements:

- Must support the `timescaledb` extension (hypertables)
- Must allow inbound connections from:
  - FastAPI host
  - Worker host(s)
  - (optional) your laptop for one-time migrations

### 2.2 Apply migrations (through revision `013`)

From your repo on any machine that can reach the production DB:

```bash
export DATABASE_URL='postgresql://...'
make db-upgrade
```

Optional sanity check:

```bash
cd services/data
poetry run alembic current
```

Expected:

- Alembic head should be `013`
- Key tables exist:
  - `paper.allocations`, `paper.pnl_events`
  - `paper.equity_fills`, `paper.equity_snapshots`
  - `paper.alerts`
  - `ml.recommendations`
  - `pm.paper_trades`, `pm.fleet_status_snapshots`, `pm.fleet_signals`
  - Polymarket runtime tables used for marks/ranking (e.g. `pm.orderbook_snapshots`, `pm.sessions`, `pm.market_metadata`)

---

## 3) Environment Variable Rules (DB_URL vs DATABASE_URL)

### Canonical rule

- **Use `DATABASE_URL` as the single source of truth**
- `DB_URL` is allowed as a fallback for older subsystems, but:
  - If both are set, they must be identical
  - If they differ, runtime will fail to avoid split-brain writes

Implementation: `packages/common/db_url.py`.

---

## 4) Deploy the API (FastAPI) on Persistent Compute

### 4.1 Where to deploy

Pick one:

- Fly.io / Render / Railway (containerized)
- A VPS (systemd)
- Kubernetes (if you already have it)

### 4.2 Required API env vars

- `DATABASE_URL` = production Postgres/Timescale URL
- `TRADING_MODE=PAPER`

Recommended:

- `DB_URL` = same as `DATABASE_URL` (only if needed for older DB_URL-gated stores)
- `REDIS_URL` = if you have Redis provisioned

If you intend to run equities paper fills via a broker path later:

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_BASE_URL=https://paper-api.alpaca.markets`

### 4.3 CORS / allowed origins

The API currently allows:

- `http://localhost:3000`
- `https://*.vercel.app`

If you add a custom domain for the dashboard, ensure the API’s CORS config includes it (`services/api/main.py`).

### 4.4 API “ready” verification (manual)

From your laptop:

```bash
curl https://<api-host>/v1/health
curl https://<api-host>/v1/metrics/summary
curl https://<api-host>/v1/alerts
```

Notes:

- Some endpoints intentionally return `501` until implemented (truthful > mock).
- Alerts may be empty until emitters fire (e.g., staleness/drawdown/kill-switch).

---

## 5) Deploy the Dashboard on Vercel

Vercel project: `caliper-dashboard`.

### 5.1 Required Vercel env vars (Production scope)

Set in Vercel → Project → Settings → Environment Variables:

- `NEXT_PUBLIC_API_URL` = `https://<api-host>/v1`
- `NEXTAUTH_URL` = `https://caliper-dashboard.vercel.app` (or your custom domain)
- `NEXTAUTH_SECRET` = generate (`openssl rand -base64 32`)

Important:

- Demo mode is disabled automatically in production (`apps/dashboard/src/lib/demo.ts`).

### 5.2 Avoid the `/v1` double-prefix pitfall

The codebase currently has mixed expectations for `NEXT_PUBLIC_API_URL`:

- The dashboard’s API client expects `NEXT_PUBLIC_API_URL` **to include** `/v1`:
  - `apps/dashboard/src/lib/api.ts` defaults to `http://localhost:8000/v1`
- The Next.js rewrite expects `NEXT_PUBLIC_API_URL` **to exclude** `/v1`:
  - `apps/dashboard/next.config.mjs` appends `/v1` again

**Phase 1 recommendation (minimal, safe):**

- Set `NEXT_PUBLIC_API_URL=https://<api-host>/v1`
- Ensure the dashboard makes requests via the API client (not via `/api/*` rewrites)

**Follow-up cleanup task (recommended before long-term production hardening):**

- Standardize on ONE convention (either always include `/v1`, or never include `/v1`) and update:
  - `apps/dashboard/next.config.mjs`
  - `vercel.json` rewrite placeholder

### 5.3 Verify the dashboard is calling your API

In the UI:

- Overview should load portfolio metrics (or a truthful backend error if the API is unreachable)
- Alerts widget should load (may be empty initially)
- Sprint-16 pages should show real ranking/fleet rows once workers are running

---

## 6) Phase 1 Worker: Paper Fleet Runner (Required)

### 6.1 What it must do

Continuously (or on a schedule):

- Build a set of strategies and run `FleetOrchestrator.process_cycle(...)`
- Persist:
  - `pm.paper_trades` (paper fills)
  - `pm.fleet_signals` (signal log)
  - `pm.fleet_status_snapshots` (heartbeat + strategy cards)

### 6.2 Current repo status (important)

- The orchestrator and stores exist: `services/fleet/orchestrator.py`, `services/fleet/paper_store.py`
- The API reads the DB snapshots:
  - `/v1/fleet/status` → `pm.fleet_status_snapshots`
  - `/v1/fleet/signals` → `pm.fleet_signals`
  - `/v1/fleet/paper-trades` → `pm.paper_trades`
- **There is not yet a production-grade CLI entrypoint** that runs the fleet loop end-to-end in real time.

### 6.3 Phase 1 action item

Implement and deploy a small runner (one binary/command) that:

- reads `DATABASE_URL`
- wires marks and market data inputs
- runs a loop (e.g., every 5–15s)
- writes snapshots to the DB

> Once this exists, the Vercel dashboard becomes “live”: fleet status, trades, and heartbeat-based alerts will start populating.

---

## 7) Phase 1 Worker: Mark Sources / Data Feed (Polymarket) (Recommended)

To compute Polymarket MTM honestly (and power ranking candidates), you need fresh:

- `pm.orderbook_snapshots` (midpoint/spread/last trade)
- `pm.sessions` / `pm.market_metadata`

### 7.1 Minimal “data-only” run mode

Run the Polymarket session in dry-run mode to record orderbooks without placing orders:

```bash
cd services/polymarket
poetry run polymarket-session --dry-run
```

Required env vars for this service (prefix `POLYMARKET_`):

- `POLYMARKET_PRIVATE_KEY` (SecretStr)
- `POLYMARKET_WALLET_ADDRESS`
- `POLYMARKET_DATABASE_URL` (or `POLYMARKET_DATABASE_URL` mapped to your prod DB)

See: `services/polymarket/config.py`, `docs/runbooks/polymarket-operations.md`.

---

## 8) Phase 1 Paper Portfolio: Funding + Snapshots

### 8.1 Allocate paper capital (manual)

Use the API:

- `POST /v1/paper/allocations` — allocates paper USD to a strategy

Example payload:

```json
{"strategy_id":"poly_mm_v2","amount_usd":"100.00","note":"initial funding"}
```

### 8.2 Snapshot policy (already in place)

Snapshot is best-effort on:

- allocation events
- fill events

And can be forced via:

- `POST /v1/paper/snapshots/compute`

Snapshots feed:

- portfolio equity curve on the homepage (`paper.equity_snapshots`, `strategy_id IS NULL`)
- per-strategy sleeve charts (when built)

---

## 9) Alerts (Operational + Safety) — Phase 1 Expectations

Alerts are DB-backed (`paper.alerts`) and emitted from:

- `/v1/metrics/summary` (best-effort):
  - Polymarket feed staleness (orderbook snapshots)
  - equities bar staleness (only if equity fills exist)
  - fleet heartbeat missed/delayed (fleet snapshots)
  - drawdown warnings/halts (based on equity snapshots)
- `/v1/controls/kill-switch` (activation/deactivation)

Phase 1 “feel real” checklist:

- Once workers are running, the Alerts widget should populate naturally.
- If nothing is running, “feed stale” and “heartbeat missed” should appear (deduped).

---

## 10) Security / Secrets (Phase 1)

### Do not store wallet private keys in Vercel

Vercel env vars are for the dashboard only. Wallet keys belong on the worker host.

### Recommended secret handling

- Use a secrets manager (platform-native) or protected `.env` on the worker host
- Use a dedicated wallet for Polymarket testing with small balance

---

## 11) Observability / Operations (Phase 1)

### Minimum

- API logs (platform logs)
- Worker logs (platform logs)
- DB monitoring (connections, storage, slow queries)

### Strongly recommended

- A “process supervisor” for workers (systemd / platform health checks)
- A simple uptime ping for:
  - API health
  - fleet heartbeat freshness (can be inferred from `pm.fleet_status_snapshots`)

---

## 12) Phase 1 End-to-End “Ready” Criteria

You are ready to run Phase 1 when:

- Dashboard on Vercel loads without demo mode
- FastAPI is reachable and connected to prod DB
- Migrations are applied through `013`
- At least one mark source is writing `pm.orderbook_snapshots`
- Fleet runner is writing `pm.fleet_status_snapshots` at a regular cadence
- Fleet runner is writing `pm.paper_trades` (paper fills)
- Portfolio snapshots (`paper.equity_snapshots`) exist and update on allocations/fills

---

## 13) Open Implementation Gaps (Phase 1)

These are known gaps you may choose to implement next:

- **Fleet runner CLI / service** (required for always-on paper trades)
- **Polymarket API routers** currently contain stubbed list/read handlers (`services/api/routers/polymarket.py`) — not required for the Phase 1 fleet loop, but needed for session analytics UI to be live
- **Model registry endpoints** are on-disk and partially placeholder (`services/api/routers/models.py`)
- **Backtests / runs** endpoints are currently `501`/empty (truthful), pending job runner

