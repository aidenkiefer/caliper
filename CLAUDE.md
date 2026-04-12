# CLAUDE.md

This file provides guidance to Claude when working with the **Caliper (quant)** codebase: a modular quantitative ML trading platform with risk management, backtesting, and live execution.

---

## Project Overview

**Caliper** is a quantitative ML trading platform for stocks (and options-ready) that emphasizes:

- **Risk management** (target level 6–7): controlled drawdowns, kill switches, circuit breakers
- **Learning and correctness** over profit maximization: interpretability, baselines, human-in-the-loop
- **Paper trading first**, then live with strict safeguards

**Current state:** Core platform **Sprints 1–9** are complete (including first ML model loop, observability, and model observatory dashboard). **Sprint 10** adds an optional **Polymarket** hourly BTC market-making service (`services/polymarket/`). **Sprints 11–14** add a **unified pipeline** (`services/portfolio/`, execution adapters), a **Polymarket feature layer** (`FeatureSnapshot`, `pm.features`), **offline CLOB simulation + evaluation** (`services/simulation/`, `services/evaluation/`, `/v1/simulation/*`, `/v1/evaluation/*`), and the **BTC probability model** (`services/ml/probability_model/`, `/v1/probability/*` — several handlers stub/mock until wired to DB). **Sprint 15** adds **regime detection + dynamic allocation** (`services/regime/`, `services/allocation/`, migration `006`, `/v1/regime/*`, `/v1/allocation/*` — **live `pm.*` reads** when `DB_URL` is set). **Sprint 16** adds **cross-sectional ranking + paper fleet** (`services/ranking/`, `services/fleet/`, migration `007`, fleet strategies under `packages/strategies/`, dashboard `sprint-16` panels); **`/v1/ranking/*`** and **`/v1/fleet/*`** return **mock** HTTP payloads until wired to ranker/orchestrator/DB reads — see **`docs/api-contracts.md`** (Sprint 15 vs 16 note). **Sprint 17** adds **reward density scoring** (`services/reward_density/` — on-chain HHI, incentive model, risk scorer, density analyzer; 5th weight term in ranker), **wallet intelligence** (`services/wallet_intelligence/` — profiling, KMeans clustering k=4, smart-money signal extraction), **composite signal aggregation** (`services/signal_aggregation/` — z-scored weighted combination, weight learning, `AggregatedSignal` in fleet strategies), and **model lifecycle management** (`services/fleet/lifecycle.py` — PAUSE/PROMOTE/DEMOTE/RETIRE rules); migration `014`; **`/v1/reward-density/*`**, **`/v1/wallet-intelligence/*`**, **`/v1/signal-aggregation/*`**, **`/v1/lifecycle/*`** are DB-backed (tables populated when scorer pipelines are driven). Shared TimescaleDB **`pm.*`** schema covers sessions, features, simulation/evaluation, probability (`005`), regime/allocation (`006`), paper trades (`007`), and Sprint 17 tables (`014`). Sprint 14 spec **AC-9** tests are **deferred** (`docs/plans/tickets/14-00-INDEX.md`). See `docs/plans/PROGRESS.md`, `docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md`, `docs/plans/summaries/SPRINT-13-SIMULATION-EVALUATION.md`, `docs/plans/summaries/SPRINT-14-PROBABILITY-MODEL.md`, `docs/plans/summaries/SPRINT-17-REWARD-DENSITY-WALLET-INTELLIGENCE.md`, and `docs/runbooks/polymarket-operations.md`. Doc map: **`docs/INDEX.md`**.

**Codebase:** Monorepo with Python services (Poetry), shared packages (common schemas, strategies), and a Next.js dashboard (npm). Trading services run separately from the dashboard; the dashboard talks to the FastAPI backend via REST.

---

## Repository Structure

```
quant/
├── apps/
│   └── dashboard/           # Next.js 14 (App Router), TypeScript, Shadcn/UI
├── services/                # Python microservices
│   ├── api/                 # FastAPI backend (REST; polymarket, features, simulation, probability, regime, ranking, fleet, reward_density, wallet_intelligence, signal_aggregation, lifecycle routers)
│   ├── allocation/          # Sprint 15: performance matrix + allocation (pm.allocation_decisions, pm.performance_matrices)
│   ├── backtest/            # Equity backtesting engine, report generator, walk-forward
│   ├── data/                # Data layer, Alembic migrations (incl. pm.* through 014)
│   ├── evaluation/          # Sprint 13: metrics, baselines, regime matrix, evaluation reports
│   ├── execution/           # OMS, broker adapter (Alpaca), position reconciliation
│   ├── features/            # Feature pipeline (equity + Polymarket FeatureSnapshot / store)
│   ├── fleet/               # Sprint 16: paper orchestrator, paper_trade store (pm.paper_trades); Sprint 17: lifecycle.py
│   ├── ml/                  # Drift, confidence gating, explainability, baselines, HITL; probability_model/ (Sprint 14)
│   ├── polymarket/          # Optional Polymarket CLOB bot (Sprint 10); not equity OMS
│   ├── portfolio/           # Sprint 11: allocator utilities for unified pipeline
│   ├── ranking/             # Sprint 16: cross-sectional ranker (universe, edge, feasibility, selection); Sprint 17: reward_density_score 5th weight term
│   ├── regime/              # Sprint 15: regime state (pm.regime_states)
│   ├── reward_density/      # Sprint 17: on-chain HHI competition, incentive model, risk scorer, density analyzer (pm.reward_density_scores)
│   ├── risk/                # RiskManager, kill switch, circuit breaker
│   ├── signal_aggregation/  # Sprint 17: z-scored composite signal aggregator with weight learning (pm.aggregated_signals)
│   ├── simulation/          # Sprint 13: CLOB replay, order book, fees, execution sim, runner
│   └── wallet_intelligence/ # Sprint 17: wallet profiling, KMeans clustering, smart-money signal extraction (pm.wallet_profiles, pm.wallet_signals)
├── packages/
│   ├── common/              # Pydantic schemas (PriceBar, Order, Signal, api_schemas, ml_schemas, execution_schemas, polymarket_schemas)
│   └── strategies/          # Strategy base, SMA Crossover, Polymarket plugins (incl. Sprint 16 fleet strategies)
├── configs/
│   ├── environments/        # .env.example, environment config
│   └── strategies/          # YAML strategy configs (e.g. sma_crossover_v1.yaml)
├── docs/                    # Architecture, contracts, runbooks, workflow
├── docs/plans/              # specs, tickets, PROGRESS.md, task_plan.md, sprint summaries
├── tests/                   # Unit and integration tests (pytest)
├── adr/                     # Architecture decision records
├── docker-compose.yml       # Postgres (TimescaleDB), Redis, API
├── Makefile                 # dev targets (api, dashboard, up, down, test)
├── pyproject.toml           # Root Poetry config
└── package.json             # Root npm (dashboard in apps/dashboard)
```

**Do not assume** `services/monitoring` matches every architecture diagram; implement only what exists under `services/` and `packages/` unless the task explicitly adds new services.

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
- **`packages/strategies`** — `Strategy` ABC: `initialize`, `on_market_data`, `generate_signals`, `risk_check`, `on_fill`, `daily_close`. Implementations include SMA Crossover (equity), Polymarket MM / unified plugins (Sprint 11+), and Sprint 16 fleet strategies (`poly_*_v1`, `poly_mm_v2`).
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
| 7 | First ML Model (End-to-End Loop) | ✅ Complete |
| 8 | ML Observability, Safety & Evaluation | ✅ Complete |
| 9 | Model Observatory Dashboard | ✅ Complete |
| 10 | Polymarket BTC Market-Making | ✅ Complete |
| 11 | Unified Pipeline Architecture | ✅ Complete |
| 12 | Polymarket Feature Layer | ✅ Complete |
| 13 | CLOB Simulation + Evaluation Engine | ✅ Complete |
| 14 | BTC Probability Model | ✅ Complete (AC-9 tests deferred) |
| 15 | Regime Detection + Dynamic Allocation | ✅ Complete |
| 16 | Cross-Sectional Ranking + Paper Fleet | ✅ Complete |
| 17 | Reward Density + Wallet Intelligence + Signal Aggregation | ✅ Complete |

Detailed tasks and verification criteria: `docs/plans/task_plan.md` and `docs/plans/DETAILED-SPRINT-PROGRESS.md`.

---

## Key Documentation (When to Use What)

| Document | Use when |
|----------|----------|
| **README.md** | Onboarding, quick start, project status, high-level structure. |
| **docs/user-guide.md** | Human-focused install, env (`DB_URL`), running API/dashboard, equities vs Polymarket, troubleshooting. |
| **docs/architecture.md** | System design, services, data flow, backtest/execution/risk flows, API structure. |
| **docs/api-contracts.md** | REST endpoints, request/response shapes, versioning, auth. |
| **docs/data-contracts.md** | Canonical schemas (price bars, orders, positions, etc.). |
| **docs/risk-policy.md** | Risk limits, kill switch, circuit breaker, order/strategy/portfolio rules. |
| **docs/dashboard-spec.md** | Dashboard pages, components, data dependencies. |
| **docs/FEATURES.md** | Implemented vs planned features, capabilities by sprint. |
| **docs/security.md** | Secrets, auth, security policies. |
| **deep-review.md** | Current ML state, pipeline explanation, implemented vs missing, recommendations. |
| **docs/plans/task_plan.md** | Sprint definitions, actionable implementation checklists, success criteria. |
| **docs/plans/DETAILED-SPRINT-PROGRESS.md** | Sprint status, checkboxes, roadmap (long-form). |
| **docs/plans/PROGRESS.md** | Milestone versions, patches, backlog (canonical log). |
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
- **API:** Routers live under `services/api/routers/`. Response models in `packages/common/api_schemas.py` and `ml_schemas.py`. Several domains still return **stub/mock** JSON (e.g. parts of simulation/evaluation/probability, **`/v1/ranking/*`**, **`/v1/fleet/*`**); **`/v1/regime/*`** and **`/v1/allocation/*`** read **live `pm.*`** when **`DB_URL`** is set — see **`docs/api-contracts.md`**.
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
- **Where to look:** `services/` for backend logic, `packages/` for shared schemas and strategies, `apps/dashboard` for the UI, `docs/` (including `docs/plans/`) for design and status.
- **What to respect:** Risk policy, Strategy and schema contracts, and the existing ML building blocks (confidence gating, SHAP, drift, baselines, HITL) when adding or changing ML-related features.
