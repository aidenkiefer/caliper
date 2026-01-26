# Quant ML Trading Platform

A modular quantitative ML trading platform for stocks and options with risk management, backtesting, and live execution capabilities.

## Project Status

**Current Phase:** Implementation - Sprint 6 ✅ COMPLETE

**Sprint 1:** ✅ Complete (Infrastructure & Data)  
**Sprint 2:** ✅ Complete (Feature Pipeline & Strategy Core)  
**Sprint 3:** ✅ Complete (Backtesting & Reporting)  
**Sprint 4:** ✅ Complete (Dashboard & API)  
**Sprint 5:** ✅ Complete (Execution & Risk)  
**Sprint 6:** ✅ Complete (ML Safety & Interpretability)

## Architecture

This is a monorepo containing:

- **`apps/dashboard`** - ✅ Next.js dashboard (Sprint 4)
- **`services/`** - Python microservices (data, features, backtest, execution, risk, monitoring, api)
- **`packages/`** - Shared libraries (common schemas, strategies, models)
- **`docs/`** - Architecture and design documentation
- **`configs/`** - Configuration files (strategies, environments)

## Technology Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL with TimescaleDB extension
- **Cache:** Redis
- **Frontend:** Next.js 14 (App Router), React, TypeScript
- **ML:** scikit-learn, XGBoost (planned), pandas/numpy for indicators

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
make dev-api
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
make dev-dashboard
```

The dashboard will be available at http://localhost:3000

### Quick Start: All Services

Start everything with Docker Compose:

```bash
# Start all services (database, redis, api)
docker-compose up -d

# Or use Makefile
make dev
```

## Project Structure

```
quant/
├── apps/
│   └── dashboard/          # ✅ Next.js dashboard (Sprint 4)
├── services/
│   ├── data/               # ✅ Data ingestion service (Sprint 1)
│   ├── features/           # ✅ Feature engineering (Sprint 2)
│   ├── backtest/           # ✅ Backtesting engine (Sprint 3)
│   ├── api/                # ✅ FastAPI backend (Sprint 4)
│   ├── execution/          # ✅ Trade execution (Sprint 5)
│   ├── risk/               # ✅ Risk management (Sprint 5)
│   ├── ml/                 # ✅ ML Safety & Interpretability (Sprint 6)
│   └── monitoring/         # Metrics & alerts (planned)
├── packages/
│   ├── common/             # ✅ Shared schemas & utilities
│   ├── strategies/         # ✅ Strategy plugins (Sprint 2)
│   └── models/             # ML model utilities (planned)
├── docs/                    # Documentation
├── configs/                 # Configuration files
├── tests/                   # Test suites
└── adr/                     # Architecture Decision Records
```

**Legend:** ✅ = Implemented | 🟡 = In Progress | ⬜ = Planned

## Documentation

### Core Documentation
- **Architecture:** [`docs/architecture.md`](docs/architecture.md)
- **Data Contracts:** [`docs/data-contracts.md`](docs/data-contracts.md)
- **API Contracts:** [`docs/api-contracts.md`](docs/api-contracts.md)
- **Risk Policy:** [`docs/risk-policy.md`](docs/risk-policy.md)
- **Security:** [`docs/security.md`](docs/security.md)
- **Dashboard Spec:** [`docs/dashboard-spec.md`](docs/dashboard-spec.md)

### Sprint Summaries
- **Sprint 1:** [`plans/SPRINT1_SUMMARY.md`](plans/SPRINT1_SUMMARY.md) - Infrastructure & Data
- **Sprint 2:** [`plans/SPRINT2_SUMMARY.md`](plans/SPRINT2_SUMMARY.md) - Feature Pipeline & Strategy Core
- **Sprint 3:** [`plans/SPRINT3_SUMMARY.md`](plans/SPRINT3_SUMMARY.md) - Backtesting & Reporting
- **Sprint 4:** [`plans/SPRINT4_SUMMARY.md`](plans/SPRINT4_SUMMARY.md) - Dashboard & API
- **Sprint 5:** [`plans/SPRINT5_SUMMARY.md`](plans/SPRINT5_SUMMARY.md) - Execution & Risk
- **Sprint 6:** [`plans/SPRINT6_SUMMARY.md`](plans/SPRINT6_SUMMARY.md) - ML Safety & Interpretability

### Multi-Agent Workflow
- **Workflow Guide:** [`docs/workflow/WORKFLOW.md`](docs/workflow/WORKFLOW.md) - Multi-agent development protocol
- **Quick Start:** [`docs/workflow/MULTI_AGENT_QUICKSTART.md`](docs/workflow/MULTI_AGENT_QUICKSTART.md)
- **Sprint 3 Prompts:** [`docs/workflow/SPRINT3_AGENT_PROMPTS.md`](docs/workflow/SPRINT3_AGENT_PROMPTS.md)
- **Sprint 4 Prompts:** [`docs/workflow/SPRINT4_AGENT_PROMPTS.md`](docs/workflow/SPRINT4_AGENT_PROMPTS.md)

### Runbooks
- **Backtest Verification:** [`docs/runbooks/backtest-verification.md`](docs/runbooks/backtest-verification.md)
- **API Verification:** [`docs/runbooks/api-verification.md`](docs/runbooks/api-verification.md)
- **Execution Verification:** [`docs/runbooks/execution-verification.md`](docs/runbooks/execution-verification.md)

### Features Overview
- **Platform Features:** [`docs/FEATURES.md`](docs/FEATURES.md) - Comprehensive feature list and capabilities

## Development Roadmap

See [`plans/task_plan.md`](plans/task_plan.md) for the full implementation plan.

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

## Security Notice

⚠️ **This platform handles real financial transactions.**
- Never commit API keys or secrets
- Use Doppler or similar secrets manager for production
- Always test in paper trading mode first
- Review risk policies before live trading

## License

[Your License Here]
