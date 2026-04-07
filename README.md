# Caliper

**Caliper** is a quantitative trading and research platform built around two complementary tracks that share the same engineering values—interpretability, baselines, strict risk discipline, and **paper or dust capital first**—and the same **Postgres/TimescaleDB** backbone for analytics.

1. **Equities (Sprints 1–9)** — Alpaca-oriented workflow: market data and features, `Strategy` plugins and backtests, ML training and inference with safety tooling (drift, confidence gating, explainability, HITL), execution through **RiskManager → OMS → Alpaca**, and a **Model Observatory** dashboard for lifecycle and evaluation.

2. **Prediction markets (Sprint 10+, optional)** — A standalone **Polymarket** service for hourly BTC **Up/Down** binary markets: market discovery, WebSocket order book + Binance reference prices, **post-only** market making with its own safety layer, rich telemetry (queue position, adverse selection, toxic flow, regime tags), and **`pm.*`** TimescaleDB schema plus REST endpoints on the main API for session analytics. It does **not** route through the equity `Strategy` / Alpaca stack; capital and controls are separate. **Sprints 11–16** add a **unified signal → allocator → execution adapter** path (incl. `services/portfolio/`), a **unified Polymarket feature layer** (`FeatureSnapshot`, `pm.features`), an **offline CLOB simulation + evaluation** stack (`services/simulation/`, `services/evaluation/`, `/v1/simulation/*`, `/v1/evaluation/*`), a **BTC probability model** (`services/ml/probability_model/`, `/v1/probability/*`), **regime detection + dynamic allocation** (`services/regime/`, `services/allocation/`, `/v1/regime/*`, `/v1/allocation/*` — **live DB reads** when `DB_URL` is set), and **cross-sectional ranking + paper fleet** (`services/ranking/`, `services/fleet/`, `/v1/ranking/*`, `/v1/fleet/*` — **mock HTTP responses** until wired to ranker/orchestrator/`pm.paper_trades` reads). See **[docs/plans/PROGRESS.md](docs/plans/PROGRESS.md)**, **[docs/api-contracts.md](docs/api-contracts.md)** (Sprint 15 vs 16 note), **[docs/plans/summaries/SPRINT-13-SIMULATION-EVALUATION.md](docs/plans/summaries/SPRINT-13-SIMULATION-EVALUATION.md)**, and **[docs/plans/summaries/SPRINT-14-PROBABILITY-MODEL.md](docs/plans/summaries/SPRINT-14-PROBABILITY-MODEL.md)** (Sprint 14 **AC-9** tests still open).

Sprint 10 is **Phase 1** of a three-phase Polymarket roadmap: collect empirical data with small size, then iterate on inventory skew, dynamic spread, and (later) directional models—see **[docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md](docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md)**.

## Project Status

**Current phase:** Core **Sprints 1–9** ✅, **Sprint 10 (Polymarket V1)** ✅ (**v2.0.0**), **Sprint 11 (unified pipeline)** ✅ (**v2.1.0**), **Sprint 12 (feature layer)** ✅ (**v2.2.0**), **Sprint 13 (simulation + evaluation)** ✅ (**v2.3.0**), **Sprint 14 (BTC probability model)** ✅ (**v2.4.0**; spec **AC-9** tests deferred), **Sprint 15 (regime + allocation)** ✅ (**v2.5.0**), **Sprint 16 (ranking + fleet)** ✅ (**v2.6.0**; ranking/fleet API still mock-backed — see **[docs/api-contracts.md](docs/api-contracts.md)**). Before funded Polymarket sessions, complete operational setup (wallet, env, migration, dry-run)—see **[docs/POLYMARKET-QUICKSTART.md](docs/POLYMARKET-QUICKSTART.md)**. Milestone table: **[docs/plans/PROGRESS.md](docs/plans/PROGRESS.md)**.

**Milestone log:** **[docs/plans/PROGRESS.md](docs/plans/PROGRESS.md)** (versions, patch notes, backlog). **Doc map:** **[docs/INDEX.md](docs/INDEX.md)**.

**Sprint 1:** ✅ Complete (Infrastructure & Data)  
**Sprint 2:** ✅ Complete (Feature Pipeline & Strategy Core)  
**Sprint 3:** ✅ Complete (Backtesting & Reporting)  
**Sprint 4:** ✅ Complete (Dashboard & API)  
**Sprint 5:** ✅ Complete (Execution & Risk)  
**Sprint 6:** ✅ Complete (ML Safety & Interpretability)  
**Sprint 7:** ✅ Complete (First ML Model – End-to-End Loop)  
**Sprint 8:** ✅ Complete (ML Observability, Safety & Evaluation)  
**Sprint 9:** ✅ Complete (Model Observatory Dashboard)  
**Sprint 10:** ✅ Complete (Polymarket BTC hourly market-making — `services/polymarket/`)  
**Sprint 11:** ✅ Complete (unified architecture — `UnifiedSignal`, `ExecutionAdapter`, `GlobalRiskManager`, `services/portfolio/`)  
**Sprint 12:** ✅ Complete (feature layer — `FeatureSnapshot`, `pm.features`, CLOB/Binance sources, feature store; tickets `12-*`)  
**Sprint 13:** ✅ Complete (CLOB simulation + evaluation — `services/simulation/`, `services/evaluation/`; tickets `13-*`)  
**Sprint 14:** ✅ Complete (BTC probability model — `services/ml/probability_model/`; **`14-11` tests not done** — see **[docs/plans/tickets/14-00-INDEX.md](docs/plans/tickets/14-00-INDEX.md)**)  
**Sprint 15:** ✅ Complete (regime + allocation — `services/regime/`, `services/allocation/`, migration `006_*`, `/v1/regime/*`, `/v1/allocation/*` — live **`pm.*`** reads when `DB_URL` set)  
**Sprint 16:** ✅ Complete (ranking + paper fleet — `services/ranking/`, `services/fleet/`, migration `007_*`, `/v1/ranking/*`, `/v1/fleet/*` mock-backed; dashboard **`apps/dashboard/src/components/sprint-16/`**)

See **[docs/SPRINTS-7-8-9-SUMMARY.md](docs/SPRINTS-7-8-9-SUMMARY.md)** for Sprints 7–9. For Polymarket: **[docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md](docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md)** (architecture, `pm.*` tables, safety, Phase 2/3 roadmap), **[docs/POLYMARKET-QUICKSTART.md](docs/POLYMARKET-QUICKSTART.md)**, **[docs/runbooks/polymarket-operations.md](docs/runbooks/polymarket-operations.md)**. For simulation/evaluation: **[docs/plans/specs/sprint-13-simulation-evaluation-spec.md](docs/plans/specs/sprint-13-simulation-evaluation-spec.md)**, **[docs/plans/summaries/SPRINT-13-SIMULATION-EVALUATION.md](docs/plans/summaries/SPRINT-13-SIMULATION-EVALUATION.md)**. For probability model: **[docs/plans/specs/sprint-14-probability-model-spec.md](docs/plans/specs/sprint-14-probability-model-spec.md)**, **[docs/plans/summaries/SPRINT-14-PROBABILITY-MODEL.md](docs/plans/summaries/SPRINT-14-PROBABILITY-MODEL.md)**. For regime/allocation + ranking/fleet: **[docs/plans/specs/sprint-15-regime-allocation-spec.md](docs/plans/specs/sprint-15-regime-allocation-spec.md)** · **[docs/plans/summaries/SPRINT-15-REGIME-ALLOCATION.md](docs/plans/summaries/SPRINT-15-REGIME-ALLOCATION.md)**, **[docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md](docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md)** · **[docs/plans/summaries/SPRINT-16-CROSS-SECTIONAL-FLEET.md](docs/plans/summaries/SPRINT-16-CROSS-SECTIONAL-FLEET.md)**, **[docs/api-contracts.md](docs/api-contracts.md)**.

## Architecture

This is a monorepo containing:

- **`apps/dashboard`** — Next.js app: platform overview, strategies, runs, health, settings, **Model Observatory** (Sprints 4, 9), **Sprint 16** panels (`apps/dashboard/src/components/sprint-16/`), and **`/platform/*`** read-only explorers (features, Polymarket sessions, regime/allocation, probability, simulation, ranking/fleet, equities hub — **`v2.6.0-p2`** / **`v2.6.0-p3`**).
- **`services/`** — Python services: **data** (migrations, including `pm.*`, simulation/evaluation, probability, regime/allocation, paper trades), **features** (incl. Polymarket sources / feature store), **backtest** (equity), **simulation** (CLOB replay / offline evaluation path), **evaluation** (metrics, baselines, reports), **portfolio** (allocator), **regime** (Sprint 15), **allocation** (Sprint 15), **ranking** (Sprint 16), **fleet** (Sprint 16 paper orchestrator + store), **execution**, **risk**, **ml** (incl. **`ml/probability_model/`** for Sprint 14), **api** (FastAPI: `/v1/polymarket/*`, `/v1/simulation/*`, `/v1/evaluation/*`, `/v1/probability/*`, `/v1/regime/*`, `/v1/allocation/*`, `/v1/ranking/*`, `/v1/fleet/*`, features router), and **`polymarket`** (Sprint 10 — optional Typer CLI `polymarket-session`, CLOB/Gamma/Binance adapters, session orchestration).
- **`packages/`** — **`common`** (shared Pydantic schemas, including `polymarket_schemas`), **`strategies`** (rule and ML strategy plugins; Sprint 16 Polymarket fleet strategies `poly_*_v1`, `poly_mm_v2`), **`models`** (stub package reserved for shared model utilities).
- **`docs/`** — Architecture, contracts, runbooks, specs, and workflow guides.
- **`configs/`** — Strategy YAML, environment templates.

## Technology Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL with TimescaleDB extension
- **Cache:** Redis
- **Frontend:** Next.js 14 (App Router), React, TypeScript
- **ML:** scikit-learn, pandas/numpy; SHAP/permutation explainers support tree models (e.g. XGBoost/LightGBM) when wired in

## Getting Started

**Step-by-step for people (install, env, both tracks):** **[docs/user-guide.md](docs/user-guide.md)**

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Poetry (Python package manager)

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd quant
   ```

2. **Start infrastructure services:**
   ```bash
   docker-compose up -d
   ```

3. **Install Python dependencies:**
   ```bash
   poetry install
   poetry shell
   ```

4. **Set up environment variables:**
   ```bash
   cp configs/environments/.env.example configs/environments/.env
   # Edit configs/environments/.env with your Alpaca API keys
   ```

5. **Run database migrations:**
   ```bash
   cd services/data
   poetry install
   poetry run alembic upgrade head

   # or from repo root:
   # make db-upgrade
   # poetry run alembic -c services/data/alembic.ini upgrade head
   ```

6. **Install Node dependencies:**
   ```bash
   npm install
   ```

### Quick Start: API Server

Start the FastAPI backend:

```bash
# Option 1: Using uvicorn directly
cd services/api
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Using Makefile
make api-dev
```

The API will be available at:
- **API Base:** http://localhost:8000
- **OpenAPI Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Quick Start: Dashboard

Start the Next.js dashboard:

```bash
# Option 1: Using npm directly
cd apps/dashboard
npm install
npm run dev

# Option 2: Using Makefile
make dashboard-dev
```

The dashboard will be available at http://localhost:3000

### Quick Start: All Services

Start everything with Docker Compose:

```bash
# Start all services (database, redis, api)
docker-compose up -d

# Or use Makefile
make up
```

## Project Structure

```
quant/
├── apps/
│   └── dashboard/          # ✅ Next.js dashboard + Model Observatory (Sprints 4, 9)
├── services/
│   ├── data/               # ✅ Data ingestion service (Sprint 1)
│   ├── features/           # ✅ Feature engineering (Sprint 2)
│   ├── backtest/           # ✅ Backtesting engine (Sprint 3)
│   ├── api/                # ✅ FastAPI backend (Sprint 4)
│   ├── execution/          # ✅ Trade execution (Sprint 5)
│   ├── risk/               # ✅ Risk management (Sprint 5)
│   ├── ml/                 # ✅ ML training, drift, gating, explainability, baselines, HITL (Sprints 6–8)
│   └── polymarket/         # ✅ Polymarket BTC hourly MM (Sprint 10; CLI, pm.* schema)
├── packages/
│   ├── common/             # ✅ Shared schemas (incl. polymarket API models)
│   ├── strategies/         # ✅ Strategy plugins (Sprint 2+; incl. ML strategy)
│   └── models/             # Stub / future shared model utilities
├── docs/                    # Documentation
├── configs/                 # Configuration files
├── tests/                   # Test suites
└── adr/                     # Architecture Decision Records
```

**Legend:** ✅ = Implemented | 🟡 = In Progress | ⬜ = Planned

## Documentation

### Core Documentation
- **Doc index (start here):** [`docs/INDEX.md`](docs/INDEX.md)
- **User guide (setup & operations):** [`docs/user-guide.md`](docs/user-guide.md)
- **Progress & versions:** [`docs/plans/PROGRESS.md`](docs/plans/PROGRESS.md)
- **Architecture:** [`docs/architecture.md`](docs/architecture.md)
- **Data Contracts:** [`docs/data-contracts.md`](docs/data-contracts.md)
- **API Contracts:** [`docs/api-contracts.md`](docs/api-contracts.md)
- **Risk Policy:** [`docs/risk-policy.md`](docs/risk-policy.md)
- **Security:** [`docs/security.md`](docs/security.md)
- **Dashboard Spec:** [`docs/dashboard-spec.md`](docs/dashboard-spec.md)

### Sprint Summaries
- **Sprint 1:** [`docs/plans/summaries/SPRINT1_SUMMARY.md`](docs/plans/summaries/SPRINT1_SUMMARY.md) - Infrastructure & Data
- **Sprint 2:** [`docs/plans/summaries/SPRINT2_SUMMARY.md`](docs/plans/summaries/SPRINT2_SUMMARY.md) - Feature Pipeline & Strategy Core
- **Sprint 3:** [`docs/plans/summaries/SPRINT3_SUMMARY.md`](docs/plans/summaries/SPRINT3_SUMMARY.md) - Backtesting & Reporting
- **Sprint 4:** [`docs/plans/summaries/SPRINT4_SUMMARY.md`](docs/plans/summaries/SPRINT4_SUMMARY.md) - Dashboard & API
- **Sprint 5:** [`docs/plans/summaries/SPRINT5_SUMMARY.md`](docs/plans/summaries/SPRINT5_SUMMARY.md) - Execution & Risk
- **Sprint 6:** [`docs/plans/summaries/SPRINT6_SUMMARY.md`](docs/plans/summaries/SPRINT6_SUMMARY.md) - ML Safety & Interpretability
- **Sprints 7–9:** [`docs/SPRINTS-7-8-9-SUMMARY.md`](docs/SPRINTS-7-8-9-SUMMARY.md) - First ML Model, Observability & Safety, Model Observatory Dashboard
- **Sprint 10:** [`docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md`](docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md) - Polymarket BTC market-making (full summary)
- **Sprint 13:** [`docs/plans/summaries/SPRINT-13-SIMULATION-EVALUATION.md`](docs/plans/summaries/SPRINT-13-SIMULATION-EVALUATION.md) - CLOB simulation + evaluation engine
- **Sprint 14:** [`docs/plans/summaries/SPRINT-14-PROBABILITY-MODEL.md`](docs/plans/summaries/SPRINT-14-PROBABILITY-MODEL.md) - BTC probability model (AC-9 tests open)
- **Sprint 15:** [`docs/plans/summaries/SPRINT-15-REGIME-ALLOCATION.md`](docs/plans/summaries/SPRINT-15-REGIME-ALLOCATION.md) - Regime detection + dynamic allocation (v2.5.0)
- **Sprint 16:** [`docs/plans/summaries/SPRINT-16-CROSS-SECTIONAL-FLEET.md`](docs/plans/summaries/SPRINT-16-CROSS-SECTIONAL-FLEET.md) - Cross-sectional ranking + paper fleet (v2.6.0)
- **Dashboard UI overhaul:** [`docs/plans/summaries/DASHBOARD-UI-OVERHAUL-2026-04.md`](docs/plans/summaries/DASHBOARD-UI-OVERHAUL-2026-04.md) — phase 1: `/start`, `/platform`, features explorer, HelpHint (`v2.6.0-p2`); phase 2: thin `/platform/*` explorers for research + Polymarket APIs (`v2.6.0-p3`)
- **Specs & tickets hub (Sprints 7–16+):** [`docs/plans/README.md`](docs/plans/README.md)

### Polymarket (Sprint 10)
- **Quick start:** [`docs/POLYMARKET-QUICKSTART.md`](docs/POLYMARKET-QUICKSTART.md)
- **Operations runbook:** [`docs/runbooks/polymarket-operations.md`](docs/runbooks/polymarket-operations.md)
- **Spec:** [`docs/plans/specs/polymarket-btc-trading-spec.md`](docs/plans/specs/polymarket-btc-trading-spec.md)
- **Early ticket batch notes:** [`docs/plans/POLYMARKET-TICKETS-1-5-SUMMARY.md`](docs/plans/POLYMARKET-TICKETS-1-5-SUMMARY.md)
- **Service docs:** [`services/polymarket/docs/`](services/polymarket/docs/) (SETUP, CONFIG, RUNBOOK)

### Multi-Agent Workflow
- **Workflow Guide:** [`docs/workflow/WORKFLOW.md`](docs/workflow/WORKFLOW.md) - Multi-agent development protocol
- **Quick Start:** [`docs/workflow/MULTI_AGENT_QUICKSTART.md`](docs/workflow/MULTI_AGENT_QUICKSTART.md)
- **Sprint 3 Prompts:** [`docs/workflow/SPRINT3_AGENT_PROMPTS.md`](docs/workflow/SPRINT3_AGENT_PROMPTS.md)
- **Sprint 4 Prompts:** [`docs/workflow/SPRINT4_AGENT_PROMPTS.md`](docs/workflow/SPRINT4_AGENT_PROMPTS.md)

### Runbooks
- **Backtest Verification:** [`docs/runbooks/backtest-verification.md`](docs/runbooks/backtest-verification.md)
- **API Verification:** [`docs/runbooks/api-verification.md`](docs/runbooks/api-verification.md)
- **Execution Verification:** [`docs/runbooks/execution-verification.md`](docs/runbooks/execution-verification.md)
- **Polymarket Operations:** [`docs/runbooks/polymarket-operations.md`](docs/runbooks/polymarket-operations.md)

### Features Overview
- **Platform Features:** [`docs/FEATURES.md`](docs/FEATURES.md) - Comprehensive feature list and capabilities

## Development Roadmap

See [`docs/plans/task_plan.md`](docs/plans/task_plan.md) for the original sprint plan and [`docs/plans/PROGRESS.md`](docs/plans/PROGRESS.md) for the current milestone log (including patch-level ship notes and backlog). Long-form checklists: [`docs/plans/DETAILED-SPRINT-PROGRESS.md`](docs/plans/DETAILED-SPRINT-PROGRESS.md).

**Sprint 1:** ✅ Infrastructure & Data (Complete)
- [x] Monorepo setup
- [x] Docker Compose with Postgres (TimescaleDB) & Redis
- [x] Shared Pydantic schemas (`packages/common/schemas.py`)
- [x] Data service with AlpacaProvider
- [x] Database migrations with Alembic
- [x] Fetch 1 year AAPL data verified in DB (250 bars)

**Sprint 2:** ✅ Feature Pipeline & Strategy Core (Complete)
- [x] Feature engineering pipeline (`services/features`)
- [x] Technical indicators (SMA, EMA, RSI, MACD, Bollinger, ATR, Stochastic)
- [x] Strategy base class (`packages/strategies/base.py`)
- [x] SMA Crossover strategy implementation
- [x] Feature engine verification
- [x] Strategy signal verification

**Sprint 3:** ✅ Backtesting & Reporting (Complete)
- [x] Backtest engine (`services/backtest/engine.py`)
- [x] Strategy integration with backtest engine
- [x] P&L calculation with accurate math
- [x] Performance metrics (Sharpe, drawdown, win rate, profit factor)
- [x] Report generation (JSON + HTML with Plotly charts)
- [x] Walk-forward optimization engine (bonus feature)
- [x] Unit tests (60+ tests)
- [x] Integration test (SMA Crossover backtest)
- [x] Documentation (README, runbook, architecture updates, ADR)

**Sprint 4:** ✅ Dashboard & API (Complete)
- [x] FastAPI backend with 10 REST endpoints (`services/api/`)
- [x] Pydantic response models (`packages/common/api_schemas.py`)
- [x] OpenAPI documentation at `/docs`
- [x] Next.js 14 dashboard (`apps/dashboard/`)
- [x] Overview, Strategies, Runs, Health, Settings pages
- [x] Shadcn/UI components + Tailwind CSS
- [x] SWR hooks for data fetching
- [x] Dark mode and responsive design
- [x] Docker configuration for API service
- [x] 160 tests (135 unit + 25 integration)

**Sprint 5:** ✅ Execution & Risk (Complete)
- [x] Execution engine (`services/execution/`)
- [x] BrokerClient interface with AlpacaClient implementation
- [x] Order Management System (OMS) with state machine
- [x] Position tracking and reconciliation
- [x] Risk management (`services/risk/`)
- [x] RiskManager with multi-level validation
- [x] Kill switch (global and per-strategy)
- [x] Circuit breaker with auto-triggers
- [x] Order and controls API endpoints
- [x] Execution schemas (`packages/common/execution_schemas.py`)
- [x] 114 tests (76 unit + 38 integration)

**Sprint 6:** ✅ ML Safety & Interpretability (Complete)
- [x] Drift detection (PSI, KL divergence, mean shift, health score)
- [x] Confidence gating with ABSTAIN signal support
- [x] SHAP explainability for tree-based models
- [x] Human-in-the-loop approval queue
- [x] Baseline strategies (hold cash, buy & hold, random)
- [x] Regret metrics vs baselines
- [x] Educational tooltips and help page
- [x] Vercel deployment configuration
- [x] ML schemas (`packages/common/ml_schemas.py`)
- [x] 70+ tests (unit + integration)

**Sprint 7:** ✅ First ML Model (End-to-End Loop) (Complete)
- [x] ML problem definition (binary next-bar direction)
- [x] Training pipeline (time-aware split, leakage prevention)
- [x] Model interface contract (input/output schemas)
- [x] Inference integration (ML strategy, confidence gating, logging)
- [x] Text-based explainability (SimpleExplainer, stored with predictions)

**Sprint 8:** ✅ ML Observability, Safety & Evaluation (Complete)
- [x] Performance tracking (prediction vs outcome, rolling accuracy, abstention rate)
- [x] Baseline & regret wiring (regret vs hold cash, buy & hold, random)
- [x] Drift monitoring (reference + current, health score, API)
- [x] SHAP/permutation explainability per prediction
- [x] Stress scenarios runbook and simulation scripts

**Sprint 9:** ✅ Model Observatory Dashboard (Complete)
- [x] Model registry UI (list view, sorting/filtering, quick actions)
- [x] Model detail page (overview, training summary, performance, health)
- [x] ML performance visualization (rolling accuracy, confidence; advanced charts extendable)
- [x] Model comparison & ranking (infrastructure and API support)
- [x] Hyperparameter & threshold tuning (API, confirmation, logging)
- [x] Model lifecycle controls (activate, pause, retire, promote, clone)
- [x] Model drift & health visualization UI
- [x] Human-in-the-loop review mode (model-centric)
- [x] Model sandbox / what-if (parameter sandbox, preview)

**Sprint 10:** ✅ Polymarket BTC hourly market-making (Complete) — **Phase 1** (data collection; Phases 2–3 = advanced MM + directional model per spec)
- [x] Parallel service `services/polymarket/` (Gamma/CLOB/Binance/**Data API** adapters, Polygon wallet + EIP-712 signing, USDC split/merge, session orchestrator, Typer CLI `polymarket-session`, `python -m polymarket`)
- [x] V1 **symmetric fixed-spread**, **post-only** quoting; 10s heartbeat (platform cancels if stale); **multi-gate safety** (session loss limit, Binance staleness, wind-down, inventory cap, emergency shutdown)
- [x] **Fee model** (pre/post Mar 30 curve); DST-aware **market discovery** for hourly BTC Up/Down windows
- [x] TimescaleDB **`pm.*`** schema: **8 tables**, **3 hypertables** (order book snapshots, Binance candles, PnL snapshots); recorder + regime tags at session end
- [x] Gap-filling analytics fields: queue-ahead estimates, adverse selection (5s/10s midpoint), toxic flow per minute, reward-eligibility proxies, quote-version attribution
- [x] FastAPI **`GET /v1/polymarket/sessions`** (+ detail, orders, fills, snapshots, PnL, toxic-flow); shared **`packages/common/polymarket_schemas.py`**
- [x] **130+** unit and **5** integration tests (mocked APIs); service docs (**SETUP**, **CONFIG**, **RUNBOOK**); run via **[docs/POLYMARKET-QUICKSTART.md](docs/POLYMARKET-QUICKSTART.md)**

**Sprint 11:** ✅ Unified architecture (Complete) — [`docs/plans/2026-04-04-unified-architecture-refactor.md`](docs/plans/2026-04-04-unified-architecture-refactor.md)
- [x] `UnifiedSignal` → `services/portfolio/` → `GlobalRiskManager` → `ExecutionAdapter` (equity vs Polymarket)

**Sprint 12:** ✅ Feature layer (Complete) — [`docs/plans/specs/sprint-12-feature-layer-spec.md`](docs/plans/specs/sprint-12-feature-layer-spec.md), tickets [`12-00-INDEX.md`](docs/plans/tickets/12-00-INDEX.md)
- [x] `FeatureSnapshot`, CLOB/Binance sources, feature builder, `pm.features`, feature store, session + API hooks

**Sprint 13:** ✅ Simulation + evaluation (Complete) — [`docs/plans/specs/sprint-13-simulation-evaluation-spec.md`](docs/plans/specs/sprint-13-simulation-evaluation-spec.md), tickets [`13-00-INDEX.md`](docs/plans/tickets/13-00-INDEX.md)
- [x] `services/simulation/` (replay, order book, fees, execution sim, adverse selection, validation, runner)
- [x] `services/evaluation/` (metrics, baselines, regime matrix, reports); Alembic `004_create_simulation_evaluation_tables.py`
- [x] `/v1/simulation/*`, `/v1/evaluation/*` (contract stubs; wire to DB + `SimulationRunner` as follow-up)

**Sprint 14:** ✅ BTC probability model (Complete; **tests incomplete**) — [`docs/plans/specs/sprint-14-probability-model-spec.md`](docs/plans/specs/sprint-14-probability-model-spec.md), task index [`14-00-INDEX.md`](docs/plans/tickets/14-00-INDEX.md)
- [x] `services/ml/probability_model/` (dataset, trainer, GBT/registry, lag tests, fee backtest, predictor, drift)
- [x] Alembic `005_create_probability_model_tables.py`; `/v1/probability/*` router (stub/mock handlers where noted)
- [ ] Spec **AC-9** — dedicated unit + integration tests (**14-11** not started)

**Sprint 15:** ✅ Regime + allocation (Complete) — [`docs/plans/specs/sprint-15-regime-allocation-spec.md`](docs/plans/specs/sprint-15-regime-allocation-spec.md), tickets [`15-00-INDEX.md`](docs/plans/tickets/15-00-INDEX.md)
- [x] `services/regime/`, `services/allocation/`; Alembic `006_create_regime_allocation_tables.py`
- [x] `/v1/regime/*`, `/v1/allocation/*` — **live reads** from `pm.regime_states`, `pm.allocation_decisions`, `pm.performance_matrices` when `DB_URL` is set

**Sprint 16:** ✅ Cross-sectional ranking + model fleet (Complete) — [`docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md`](docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md), tickets [`16-00-INDEX.md`](docs/plans/tickets/16-00-INDEX.md)
- [x] `services/ranking/` (universe, edge, feasibility, scoring, selection); `services/fleet/` (orchestrator, `PaperTradeStore`, `pm.paper_trades`); migration `007_create_pm_paper_trades_table.py`
- [x] Fleet strategies under `packages/strategies/`; dashboard panels `apps/dashboard/src/components/sprint-16/`
- [x] `/v1/ranking/*`, `/v1/fleet/*` — **contract + mock payloads**; wiring to `MarketRanker` / orchestrator / DB reads tracked in **[docs/api-contracts.md](docs/api-contracts.md)** and backlog **[docs/plans/PROGRESS.md](docs/plans/PROGRESS.md)**

## Security Notice

⚠️ **This platform handles real financial transactions.**
- Never commit API keys or secrets
- Use Doppler or similar secrets manager for production
- Always test in paper trading mode first (Alpaca); for Polymarket, use **`--dry-run`** and dust capital before scaling
- Review risk policies before live trading (`docs/risk-policy.md` applies to equity paths; Polymarket uses its own safety limits in config — see runbook)

## License

[Your License Here]
