# Quant ML Trading Platform

A modular quantitative ML trading platform for stocks and options with risk management, backtesting, and live execution capabilities.

## Project Status

**Current Phase:** Implementation - Sprint 3 ✅ COMPLETE

**Sprint 1:** ✅ Complete (Infrastructure & Data)  
**Sprint 2:** ✅ Complete (Feature Pipeline & Strategy Core)  
**Sprint 3:** ✅ Complete (Backtesting & Reporting)

## Architecture

This is a monorepo containing:

- **`apps/dashboard`** - Next.js dashboard (Vercel deployment)
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

7. **Start the dashboard (when implemented):**
   ```bash
   npm run dev
   ```

## Project Structure

```
quant/
├── apps/
│   └── dashboard/          # Next.js dashboard (planned)
├── services/
│   ├── data/               # ✅ Data ingestion service (Sprint 1)
│   ├── features/           # ✅ Feature engineering (Sprint 2)
│   ├── backtest/           # ✅ Backtesting engine (Sprint 3)
│   ├── api/                # FastAPI backend (Sprint 4)
│   ├── execution/          # Trade execution (Sprint 5)
│   ├── risk/               # Risk management (Sprint 5)
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
- **Sprint 1:** [`SPRINT1_SUMMARY.md`](SPRINT1_SUMMARY.md) - Infrastructure & Data
- **Sprint 2:** [`SPRINT2_SUMMARY.md`](SPRINT2_SUMMARY.md) - Feature Pipeline & Strategy Core
- **Sprint 3:** [`SPRINT3_SUMMARY.md`](SPRINT3_SUMMARY.md) - Backtesting & Reporting

### Multi-Agent Workflow
- **Workflow Guide:** [`docs/WORKFLOW.md`](docs/WORKFLOW.md) - Multi-agent development protocol
- **Quick Start:** [`docs/MULTI_AGENT_QUICKSTART.md`](docs/MULTI_AGENT_QUICKSTART.md)
- **Sprint 3 Prompts:** [`docs/SPRINT3_AGENT_PROMPTS.md`](docs/SPRINT3_AGENT_PROMPTS.md)

### Runbooks
- **Backtest Verification:** [`docs/runbooks/backtest-verification.md`](docs/runbooks/backtest-verification.md)

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

## Security Notice

⚠️ **This platform handles real financial transactions.**
- Never commit API keys or secrets
- Use Doppler or similar secrets manager for production
- Always test in paper trading mode first
- Review risk policies before live trading

## License

[Your License Here]
