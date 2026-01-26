# Quant ML Trading Platform

A modular quantitative ML trading platform for stocks and options with risk management, backtesting, and live execution capabilities.

## Project Status

**Current Phase:** Implementation - Sprint 1 (Infrastructure & Data)

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
- **ML:** scikit-learn, XGBoost, pandas-ta

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
   cp configs/environments/.env.example .env.local
   # Edit .env.local with your configuration
   ```

5. **Run database migrations:**
   ```bash
   cd services/data
   alembic upgrade head
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
│   └── dashboard/          # Next.js dashboard
├── services/
│   ├── api/                # FastAPI backend
│   ├── data/               # Data ingestion service
│   ├── features/           # Feature engineering
│   ├── backtest/           # Backtesting engine
│   ├── execution/          # Trade execution
│   ├── risk/               # Risk management
│   └── monitoring/        # Metrics & alerts
├── packages/
│   ├── common/             # Shared schemas & utilities
│   ├── strategies/         # Strategy plugins
│   └── models/             # ML model utilities
├── docs/                    # Documentation
├── configs/                 # Configuration files
└── tests/                   # Test suites
```

## Documentation

- **Architecture:** [`docs/architecture.md`](docs/architecture.md)
- **Data Contracts:** [`docs/data-contracts.md`](docs/data-contracts.md)
- **API Contracts:** [`docs/api-contracts.md`](docs/api-contracts.md)
- **Risk Policy:** [`docs/risk-policy.md`](docs/risk-policy.md)
- **Security:** [`docs/security.md`](docs/security.md)
- **Dashboard Spec:** [`docs/dashboard-spec.md`](docs/dashboard-spec.md)

## Development Roadmap

See [`plans/task_plan.md`](plans/task_plan.md) for the full implementation plan.

**Sprint 1 (Current):** Infrastructure & Data
- [x] Monorepo setup
- [ ] Docker Compose with Postgres & Redis
- [ ] Shared Pydantic schemas
- [ ] Data service with AlpacaProvider
- [ ] Database migrations

## Security Notice

⚠️ **This platform handles real financial transactions.**
- Never commit API keys or secrets
- Use Doppler or similar secrets manager for production
- Always test in paper trading mode first
- Review risk policies before live trading

## License

[Your License Here]
