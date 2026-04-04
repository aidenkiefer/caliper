# Caliper

**Caliper** is a quantitative trading and research platform built around two complementary tracks that share the same engineering values—interpretability, baselines, strict risk discipline, and **paper or dust capital first**—and the same **Postgres/TimescaleDB** backbone for analytics.

1. **Equities (Sprints 1–9)** — Alpaca-oriented workflow: market data and features, `Strategy` plugins and backtests, ML training and inference with safety tooling (drift, confidence gating, explainability, HITL), execution through **RiskManager → OMS → Alpaca**, and a **Model Observatory** dashboard for lifecycle and evaluation.

2. **Prediction markets (Sprint 10, optional)** — A standalone **Polymarket** service for hourly BTC **Up/Down** binary markets: market discovery, WebSocket order book + Binance reference prices, **post-only** market making with its own safety layer, rich telemetry (queue position, adverse selection, toxic flow, regime tags), and **`pm.*`** TimescaleDB schema plus REST endpoints on the main API for session analytics. It does **not** route through the equity `Strategy` / Alpaca stack; capital and controls are separate.

Sprint 10 is **Phase 1** of a three-phase Polymarket roadmap: collect empirical data with small size, then iterate on inventory skew, dynamic spread, and (later) directional models—see **[docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md](docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md)**.

## Project Status

**Current phase:** Core platform **Sprints 1–9** ✅ and **Sprint 10 (Polymarket V1)** ✅ complete (**v2.0.0** milestone). Before funded Polymarket sessions, complete operational setup (wallet, env, migration, dry-run)—see **[docs/POLYMARKET-QUICKSTART.md](docs/POLYMARKET-QUICKSTART.md)**.

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

See **[docs/SPRINTS-7-8-9-SUMMARY.md](docs/SPRINTS-7-8-9-SUMMARY.md)** for Sprints 7–9. For Polymarket: **[docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md](docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md)** (architecture, `pm.*` tables, safety, Phase 2/3 roadmap), **[docs/POLYMARKET-QUICKSTART.md](docs/POLYMARKET-QUICKSTART.md)**, **[docs/runbooks/polymarket-operations.md](docs/runbooks/polymarket-operations.md)**.

## Architecture

This is a monorepo containing:

- **`apps/dashboard`** — Next.js app: platform overview, strategies, runs, health, settings, and **Model Observatory** (Sprints 4, 9).
- **`services/`** — Python services: **data** (migrations, including `pm.*`), **features**, **backtest**, **execution**, **risk**, **ml**, **api** (FastAPI, including `/v1/polymarket/*`), and **`polymarket`** (Sprint 10 — optional Typer CLI `polymarket-session`, CLOB/Gamma/Binance adapters, session orchestration).
- **`packages/`** — **`common`** (shared Pydantic schemas, including `polymarket_schemas`), **`strategies`** (rule and ML strategy plugins), **`models`** (stub package reserved for shared model utilities).
- **`docs/`** — Architecture, contracts, runbooks, specs, and workflow guides.
- **`configs/`** — Strategy YAML, environment templates.

## Technology Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL with TimescaleDB extension
- **Cache:** Redis
- **Frontend:** Next.js 14 (App Router), React, TypeScript
- **ML:** scikit-learn, pandas/numpy; SHAP/permutation explainers support tree models (e.g. XGBoost/LightGBM) when wired in

## Getting Started

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
   poetry run alembic upgrade head
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
- **Specs & tickets hub (Sprints 7–10):** [`docs/plans/README.md`](docs/plans/README.md)

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

## Security Notice

⚠️ **This platform handles real financial transactions.**
- Never commit API keys or secrets
- Use Doppler or similar secrets manager for production
- Always test in paper trading mode first (Alpaca); for Polymarket, use **`--dry-run`** and dust capital before scaling
- Review risk policies before live trading (`docs/risk-policy.md` applies to equity paths; Polymarket uses its own safety limits in config — see runbook)

## License

[Your License Here]
