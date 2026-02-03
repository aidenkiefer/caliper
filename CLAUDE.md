# CLAUDE.md

This file provides guidance to Claude when working with the **Caliper (quant)** codebase: a modular quantitative ML trading platform with risk management, backtesting, and live execution.

---

## Project Overview

**Caliper** is a quantitative ML trading platform for stocks (and options-ready) that emphasizes:

- **Risk management** (target level 6–7): controlled drawdowns, kill switches, circuit breakers
- **Learning and correctness** over profit maximization: interpretability, baselines, human-in-the-loop
- **Paper trading first**, then live with strict safeguards

**Current state:** Sprints 1–6 are complete. The only live strategy is **SMA Crossover** (rule-based; no trained ML model yet). ML infrastructure (confidence gating, SHAP, drift detection, baselines, HITL) exists but is not wired to a model. Sprint 7 will introduce the first ML model end-to-end; Sprints 8–9 add observability and the model-centric dashboard.

**Codebase:** Monorepo with Python services (Poetry), shared packages (common schemas, strategies), and a Next.js dashboard (npm). Trading services run separately from the dashboard; the dashboard talks to the FastAPI backend via REST.

---

## Repository Structure

```
quant/
├── apps/
│   └── dashboard/           # Next.js 14 (App Router), TypeScript, Shadcn/UI
├── services/                # Python microservices
│   ├── api/                 # FastAPI backend (REST for dashboard)
│   ├── backtest/            # Backtesting engine, report generator, walk-forward
│   ├── execution/           # OMS, broker adapter (Alpaca), position reconciliation
│   ├── features/           # Feature pipeline (indicators, 30+ features)
│   ├── ml/                  # Drift, confidence gating, explainability, baselines, HITL
│   └── risk/                # RiskManager, kill switch, circuit breaker
├── packages/
│   ├── common/              # Pydantic schemas (PriceBar, Order, Signal, api_schemas, ml_schemas, execution_schemas)
│   └── strategies/          # Strategy base class, SMA Crossover strategy
├── configs/
│   ├── environments/        # .env.example, environment config
│   └── strategies/          # YAML strategy configs (e.g. sma_crossover_v1.yaml)
├── docs/                    # Architecture, contracts, runbooks, workflow
├── plans/                   # task_plan.md, progress.md, sprint summaries
├── tests/                   # Unit and integration tests (pytest)
├── adr/                     # Architecture decision records
├── docker-compose.yml       # Postgres (TimescaleDB), Redis, API
├── Makefile                 # dev targets (api, dashboard, up, down, test)
├── pyproject.toml           # Root Poetry config
└── package.json             # Root npm (dashboard in apps/dashboard)
```

**Do not assume** a `services/data` or `services/monitoring` directory exists in the same way as in the architecture doc; implement only what exists under `services/` and `packages/` unless the task explicitly adds new services.

---

## Technology Stack

| Layer        | Technology |
|-------------|------------|
| Backend     | Python 3.11+, FastAPI, Pydantic |
| Database    | PostgreSQL with TimescaleDB, Redis |
| Data/ML     | pandas, numpy, scikit-learn, SHAP (XGBoost planned) |
| Strategies   | `packages/strategies` (Strategy ABC, SMA Crossover) |
| Dashboard   | Next.js 14 (App Router), React, TypeScript, Tailwind, Shadcn/UI, SWR |
| Broker      | Alpaca (paper) via `BrokerClient` abstraction |
| Deployment  | Dashboard → Vercel; trading services → Docker/VM |

---

## Commands

**Infrastructure and API:**

```bash
make up              # Start Postgres, Redis, API (docker-compose up -d)
make down            # Stop all services
make api-dev         # Start API in Docker (http://localhost:8000)
make logs            # Follow all service logs
make logs-api        # API logs only
```

**API server (local, from repo root):**

```bash
cd services/api && poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Or: make dev-api (if defined)
```

**Dashboard:**

```bash
make dashboard-dev   # cd apps/dashboard && npm run dev
# Or: cd apps/dashboard && npm install && npm run dev
# Dashboard: http://localhost:3000
```

**Python and tests:**

```bash
poetry install       # Install Python deps (from repo root)
poetry shell         # Activate env
poetry run pytest tests/ -v                    # All tests
poetry run pytest tests/unit/ -v                # Unit only
poetry run pytest tests/integration/ -v         # Integration only
make test-execution  # Execution + risk unit tests
```

**Database (when applicable):**

```bash
cd services/data && poetry run alembic upgrade head   # Migrations
```

---

## Architecture (Summary)

**Data flow (conceptual):** Market data → (optional) feature pipeline → Strategy → Signals → RiskManager → Orders → OMS → Broker. Backtest path: historical bars → Strategy → same risk/order simulation → metrics and reports.

**Services you will touch most:**

- **`services/api`** — FastAPI app, routers for health, metrics, strategies, runs, positions, orders, controls, drift, explanations, baselines, recommendations. Currently uses mock data and stub DB/auth; see `dependencies.py`.
- **`services/backtest`** — `BacktestEngine` runs a `Strategy` over bars; `ReportGenerator` produces JSON/HTML; `WalkForwardEngine` for parameter optimization. Handles ABSTAIN signals (tracked, filtered before risk check).
- **`services/execution`** — OMS, `BrokerClient` (Alpaca implementation), order state machine, position reconciliation.
- **`services/risk`** — `RiskManager` (order/strategy/portfolio limits), `KillSwitch`, `CircuitBreaker`. See `docs/risk-policy.md`.
- **`services/ml`** — Drift (PSI, KL, health score), confidence gating (BUY/SELL/ABSTAIN), explainability (SHAP, permutation), baselines (hold cash, buy & hold, random), regret calculator, HITL approval queue. Ready for use once a model is integrated.
- **`packages/strategies`** — `Strategy` ABC: `initialize`, `on_market_data`, `generate_signals`, `risk_check`, `on_fill`, `daily_close`. Only implementation: SMA Crossover (rule-based).
- **`packages/common`** — Shared Pydantic schemas: `schemas.py` (PriceBar, Order, Position, Signal, etc.), `api_schemas.py`, `ml_schemas.py`, `execution_schemas.py`.

**Important:** The backtest engine does **not** call the feature pipeline; SMA Crossover uses raw bars and its own SMA math. When adding an ML strategy, you would feed features into a model and optionally use the feature pipeline inside the backtest loop.

---

## Key Technical Details

**Strategy interface:** All strategies implement `Strategy` in `packages/strategies/base.py`. They consume `PriceBar` and `PortfolioState`, return `List[Signal]` (symbol, side BUY/SELL/ABSTAIN, strength, etc.), and `risk_check` turns signals into `List[Order]`. The backtest engine records ABSTAIN and excludes it from orders.

**Signals and orders:** `Signal.side` can be `"BUY"`, `"SELL"`, or `"ABSTAIN"`. Orders are validated by `RiskManager` then sent to the broker. Order lifecycle: PENDING → SUBMITTED → FILLED | REJECTED | CANCELLED. Idempotency via `client_order_id`.

**Risk:** Limits are defined in `docs/risk-policy.md`. Pre-trade checks: kill switch → order limits → strategy limits → portfolio limits. Circuit breaker and kill switch can auto-trigger on drawdown thresholds.

**Config:** Strategy configs live in `configs/strategies/*.yaml` (e.g. `sma_crossover_v1.yaml`). Environment and secrets: `configs/environments/.env.example`; never commit real keys.

**ML (current):** No trained model is loaded or used for trading. Confidence gating, SHAP, drift, baselines, and HITL are implemented as libraries/schemas; wire them when adding the first ML model (Sprint 7).

---

## Sprint Roadmap

| Sprint | Focus | Status |
|--------|--------|--------|
| 1 | Infrastructure & Data | ✅ Complete |
| 2 | Feature Pipeline & Strategy Core | ✅ Complete |
| 3 | Backtesting & Reporting | ✅ Complete |
| 4 | Dashboard & API | ✅ Complete |
| 5 | Execution & Risk | ✅ Complete |
| 6 | ML Safety & Interpretability | ✅ Complete |
| 7 | First ML Model (End-to-End Loop) | Not Started |
| 8 | ML Observability, Safety & Evaluation | Not Started |
| 9 | Model Observatory Dashboard | Not Started |

Detailed tasks and verification criteria: `plans/task_plan.md` and `plans/progress.md`.

---

## Key Documentation (When to Use What)

| Document | Use when |
|----------|----------|
| **README.md** | Onboarding, quick start, project status, high-level structure. |
| **docs/architecture.md** | System design, services, data flow, backtest/execution/risk flows, API structure. |
| **docs/api-contracts.md** | REST endpoints, request/response shapes, versioning, auth. |
| **docs/data-contracts.md** | Canonical schemas (price bars, orders, positions, etc.). |
| **docs/risk-policy.md** | Risk limits, kill switch, circuit breaker, order/strategy/portfolio rules. |
| **docs/dashboard-spec.md** | Dashboard pages, components, data dependencies. |
| **docs/FEATURES.md** | Implemented vs planned features, capabilities by sprint. |
| **docs/security.md** | Secrets, auth, security policies. |
| **deep-review.md** | Current ML state, pipeline explanation, implemented vs missing, recommendations. |
| **plans/task_plan.md** | Sprint definitions, actionable implementation checklists, success criteria. |
| **plans/progress.md** | Sprint status, checkboxes, roadmap, next actions. |
| **docs/runbooks/backtest-verification.md** | How to verify backtest engine and P&L. |
| **docs/runbooks/api-verification.md** | How to verify API endpoints. |
| **docs/runbooks/execution-verification.md** | How to verify execution and risk. |
| **docs/runbooks/ml-safety-verification.md** | How to verify drift, confidence, explainability, HITL. |
| **adr/** | Architecture decisions (e.g. monorepo, TimescaleDB, backtest engine choice). |

---

## Conventions and Practices

- **Imports:** Python code runs with the repo root on `sys.path` (e.g. `packages.common.schemas`, `packages.strategies.base`). Use package names, not relative paths that assume a specific CWD.
- **Schemas:** Prefer Pydantic models from `packages/common` for all API and cross-service data. Do not invent ad-hoc dicts for contracts that are already defined.
- **Strategies:** New strategies go in `packages/strategies`, implement the `Strategy` ABC, and can be configured via YAML in `configs/strategies/`. Backtest and execution both use the same interface.
- **Risk:** Any path that creates orders must go through `RiskManager.check_order`. Respect kill switch and circuit breaker; do not bypass for “testing” in production code.
- **API:** Routers live under `services/api/routers/`. Response models in `packages/common/api_schemas.py` and `ml_schemas.py`. Currently the API serves mock data; replacing with real DB is a planned step.
- **Testing:** Unit tests in `tests/unit/`, integration in `tests/integration/`. Fixtures in `tests/fixtures/`. Run with `poetry run pytest tests/ -v`.
- **Dashboard:** Next.js app in `apps/dashboard`; use existing Shadcn/UI and SWR hooks where possible. API base URL via `NEXT_PUBLIC_API_URL` or equivalent.

---

## Skills

When the task involves rules, workflows, or multi-step processes, use the skills under `agents/skills/skills/` if available. Start with `agents/skills/skills/using-superpowers/SKILL.md` to see how and when to invoke skills.

---

## Tool Use

Use the minimum number of tool calls needed to complete the task. Prefer reading the specific files or docs that are relevant (see table above) rather than scanning the whole repo. Do not run destructive or production commands (e.g. live trading, real money) or commit secrets.

---

## No Review, Verification, or QA — Not Allowed

**Claude is NOT ALLOWED to review, verify, or perform QA on code.** That is the user’s job.

- Do **not** run `npm run build`, `npm run dev`, `npm test`, `poetry run pytest`, `poetry run uvicorn`, or any other build, compile, test, or run command to “verify” or “confirm” changes.
- Do **not** offer to “run the tests,” “run a quick build to verify,” or “double-check the implementation.”
- Do **not** re-read the full file after editing to “verify” the change or perform a self-review.
- Do **not** claim that work is “verified” or “tested” on the basis of having run commands.

Review, verification, and quality assurance are **exclusively the user’s responsibility**. Assume your edits are correct and leave all verification to them. If you need to read a file to implement the next step, that is fine—but do not run the project or the test suite, and do not perform review or QA.

---

## No Build or Compile Commands

**Claude must NOT run commands that build or compile code.**

- Do **not** run `npm run build`, `npm run build:store`, `npm run build:ui`, `poetry build`, or any equivalent build/compile step.
- Do **not** run linters, formatters, or type checkers as a “verification” step (e.g. `npm run lint`, `poetry run mypy`) unless the user explicitly asks you to run a specific command.

Testing and QA are handled by the human. Running builds and tests burns tokens and is unnecessary; assume your edits are correct and leave verification to them.

---

## Summary

- **What this is:** A quantitative ML trading platform (Caliper/quant) with backtest, execution, risk, and ML safety infrastructure. One rule-based strategy (SMA Crossover) is live; the first ML model is planned for Sprint 7.
- **Where to look:** `services/` for backend logic, `packages/` for shared schemas and strategies, `apps/dashboard` for the UI, `docs/` and `plans/` for design and status.
- **What to respect:** Risk policy, Strategy and schema contracts, and the existing ML building blocks (confidence gating, SHAP, drift, baselines, HITL) when adding or changing ML-related features.
