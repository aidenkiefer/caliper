# Platform Features Overview

**Last Updated:** 2026-04-06  
**Status:** Sprints 1–16 shipped — through **v2.6.0** (ranking + paper fleet); Sprint 14 spec **AC-9** tests **not yet added**; **`/v1/ranking/*`** and **`/v1/fleet/*`** remain **mock-backed** at the HTTP layer — see **[docs/api-contracts.md](api-contracts.md)** and **[docs/plans/PROGRESS.md](plans/PROGRESS.md)**

This document provides a comprehensive overview of all implemented features, capabilities, and components in Caliper.

For a concise summary of **Sprints 7–9** (First ML Model, Observability & Safety, Model Observatory Dashboard), see **[docs/SPRINTS-7-8-9-SUMMARY.md](SPRINTS-7-8-9-SUMMARY.md)**.

---

## 🎯 Current Implementation Status

### ✅ Completed (Sprints 1–16; Sprint 14 tests incomplete; Sprint 16 ranking/fleet API mock)

#### Sprint 1: Infrastructure & Data ✅
- **Monorepo Structure**: Complete Python/Node.js monorepo with Poetry and npm
- **Docker Infrastructure**: PostgreSQL (TimescaleDB) + Redis via docker-compose
- **Data Service**: Market data ingestion service (`services/data`)
  - AlpacaProvider for historical data fetching
  - Database integration with Alembic migrations
  - TimescaleDB hypertables for time-series data
  - Data validation via Pydantic schemas
- **Shared Schemas**: Common data contracts (`packages/common/schemas.py`)
  - PriceBar, Order, Position, Signal schemas
  - Trading mode enums and type definitions

#### Sprint 2: Feature Pipeline & Strategy Core ✅
- **Feature Engineering Service** (`services/features`)
  - Technical Indicators (7 core indicators):
    - SMA (Simple Moving Average)
    - EMA (Exponential Moving Average)
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands
    - ATR (Average True Range)
    - Stochastic Oscillator
  - Feature Pipeline (`FeaturePipeline` class)
    - Computes 30+ features from price bars
    - Derived features (returns, volatility, crossovers)
    - Feature caching support
    - Pandas/numpy-based implementation (Python 3.11 compatible)
- **Strategy Framework** (`packages/strategies`)
  - Abstract Strategy base class (`Strategy`)
    - Full lifecycle methods (initialize, on_market_data, generate_signals, risk_check, on_fill, daily_close)
    - Signal generation interface
    - Portfolio state management
  - SMA Crossover Strategy (Starter Strategy)
    - Golden cross (buy) and death cross (sell) detection
    - Position sizing based on equity percentage
    - Risk checks and order generation
    - YAML-based configuration
- **Configuration System**
  - Strategy configs in YAML format
  - Environment variables management

#### Sprint 3: Backtesting & Reporting ✅
- **Backtest Engine** (`services/backtest/engine.py`)
  - Strategy execution on historical data
  - Order fill simulation (market orders with slippage)
  - Commission modeling ($1.00 per trade default)
  - Slippage modeling (10 bps default)
  - Position tracking
  - Date range filtering
  - Equity curve generation
- **P&L Calculation**
  - Trade-level P&L with accurate math
  - Portfolio-level equity tracking
  - Performance metrics computation:
    - Total return (absolute and percentage)
    - Sharpe ratio (annualized)
    - Max drawdown (absolute and percentage)
    - Win rate
    - Profit factor
    - Average win/loss
    - Trade statistics
- **Report Generation** (`services/backtest/report.py`)
  - JSON reports (machine-readable)
  - HTML reports (human-readable with Plotly charts)
  - Interactive equity curve visualization
  - Trade list with P&L breakdown
  - Performance metrics display
- **Walk-Forward Optimization** (`services/backtest/walk_forward.py`) ⭐ Bonus Feature
  - Rolling and anchored window types
  - Grid search parameter optimization
  - Multiple optimization objectives (Sharpe, returns, profit factor, win rate, drawdown)
  - Parameter stability analysis
  - Aggregated out-of-sample metrics
- **Testing & Verification**
  - 60+ unit tests covering engine, P&L, reports
  - Integration test for SMA Crossover backtest
  - Known-good P&L validation scenarios
  - Comprehensive test fixtures

#### Sprint 4: Dashboard & API ✅
- **FastAPI Backend** (`services/api/`)
  - 10+ REST endpoints per `docs/api-contracts.md`
  - Health, metrics, strategies, runs, positions endpoints
  - Pydantic response models (`packages/common/api_schemas.py`)
  - CORS middleware for dashboard access
  - OpenAPI documentation at `/docs`
- **Next.js Dashboard** (`apps/dashboard/`)
  - Next.js 14 with App Router
  - Overview, Strategies, Runs, Health, Settings pages
  - Shadcn/UI components + Tailwind CSS
  - SWR hooks for data fetching with polling
  - Dark mode and responsive design
  - Interactive equity curve charts
  - **UI phase 1 (v2.6.0-p2):** **`/start`** linear checklist (localStorage), **`/platform`** capability hub with search + status badges, **`/platform/features`** read-only `FeatureSnapshot` explorer; shared **`HelpHint`** (`?` → tooltip on desktop, bottom sheet on narrow screens); dynamic page titles via **`DashboardFrame`**; Overview **Mock** badge on Sprint 16 fleet card.
  - **UI phase 2 (v2.6.0-p3):** Thin explorers under **`/platform/polymarket`** (list + session detail/orders/fills), **`/platform/regime-allocation`**, **`/platform/probability`**, **`/platform/simulation`**, **`/platform/ranking-fleet`**, **`/platform/equities`**; shared **`ExplorerPageHeader`** + **`JsonBlock`**; hub rows link to these routes via **`platform-capabilities.ts`**. Summary: [DASHBOARD-UI-OVERHAUL-2026-04.md](plans/summaries/DASHBOARD-UI-OVERHAUL-2026-04.md).
- **Testing & Verification**
  - 160 tests (135 unit + 25 integration)
  - API endpoint validation
  - Mock data for development

#### Sprint 5: Execution & Risk ✅
- **Execution Engine** (`services/execution/`)
  - BrokerClient abstract interface with adapter pattern
  - AlpacaClient implementation for Alpaca Paper API
  - Order Management System (OMS) with state machine
  - Order states: PENDING → SUBMITTED → FILLED/PARTIALLY_FILLED/REJECTED/CANCELLED
  - Order idempotency via unique `client_order_id`
  - Position tracking and reconciliation
- **Risk Management** (`services/risk/`)
  - RiskManager with multi-level pre-trade validation
  - Portfolio-level limits:
    - 3% daily drawdown (circuit breaker trigger)
    - 10% total drawdown (kill switch trigger)
    - 80% max capital deployed
    - 20 max open positions
  - Order-level limits:
    - 2% max risk per trade
    - $25,000 max notional per trade
    - $5.00 minimum stock price (penny stock filter)
    - 5% max price deviation from last traded price
  - Strategy-level limits:
    - Max allocation percentage
    - Daily loss limits
    - Strategy pause capability
  - KillSwitch (global and per-strategy)
  - CircuitBreaker with auto-triggers
  - Admin code required for deactivation
- **API Endpoints**
  - POST /v1/orders (submit with risk validation)
  - GET /v1/orders (list with pagination)
  - GET /v1/orders/{order_id} (details)
  - DELETE /v1/orders/{order_id} (cancel)
  - POST /v1/controls/kill-switch (activate/deactivate)
  - GET /v1/controls/kill-switch (status)
  - POST /v1/controls/mode-transition (PAPER → LIVE)
- **Testing & Verification**
  - 114 tests (76 unit + 38 integration)
  - Risk rejection scenarios validated
  - Kill switch and circuit breaker behavior tested

#### Sprint 6: ML Safety & Interpretability ✅
- **Drift Detection Service** (`services/ml/drift/`)
  - PSI (Population Stability Index) calculation
  - KL divergence for distribution comparison
  - Mean shift detection (in standard deviations)
  - Confidence drift monitoring
  - Error drift tracking (when ground truth available)
  - Health score calculator (0-100 composite score)
  - Threshold-based alerts (WARNING/CRITICAL)
- **Confidence Gating** (`services/ml/confidence/`)
  - ABSTAIN signal support in model output
  - Configurable confidence thresholds per strategy
  - Entropy and uncertainty measures
  - Ensemble disagreement signals
  - Abstention tracking in backtests
- **Explainability Service** (`services/ml/explainability/`)
  - SHAP integration for tree-based models
  - Permutation importance fallback
  - Trade explanation payloads (features, contributions, directions)
  - Explanation storage with trades
- **Baseline Strategies** (`services/ml/baselines/`)
  - Hold cash baseline (0% return)
  - Buy & hold baseline (market tracking)
  - Random baseline (risk-controlled)
  - Regret calculator (strategy vs baselines)
- **Human-in-the-Loop** (`services/ml/hitl/`)
  - Recommendation approval queue
  - Human decision logging (approve/reject with rationale)
  - Agreement statistics (human vs model)
- **API Endpoints**
  - GET /v1/drift/metrics/{model_id}
  - GET /v1/drift/health/{model_id}
  - GET /v1/explanations/{trade_id}
  - GET /v1/baselines/comparison
  - GET/POST /v1/recommendations (HITL queue)
- **Dashboard Features**
  - Help page with searchable glossary (22 trading terms)
  - Educational tooltips on all metrics
  - Trade explanation UI with feature importance charts
  - Approval queue page for HITL
  - Baseline comparison widget
- **Vercel Deployment**
  - vercel.json configuration
  - API rewrites to FastAPI backend
  - Security headers
  - Deployment runbook
- **Testing & Verification**
  - 70+ tests (unit + integration)
  - ML safety verification runbook

#### Sprints 7–9: First ML Model, Observability & Safety, Model Observatory ✅
- **Sprint 7:** First ML model end-to-end (problem definition, training pipeline, model interface contract, inference via `MLDirectionStrategyV1`, text explainability). See [sprint-7-ml-problem-definition.md](sprint-7-ml-problem-definition.md), [model-interface-contract.md](model-interface-contract.md), [sprint-7-inference-and-explainability.md](sprint-7-inference-and-explainability.md), [using-ml-strategy.md](using-ml-strategy.md).
- **Sprint 8:** Performance tracking, baseline/regret wiring, drift monitoring, SHAP/permutation explainability per prediction, stress-scenarios runbook and simulation. See [sprint-8-implementation-summary.md](sprint-8-implementation-summary.md), [runbooks/stress-scenarios.md](runbooks/stress-scenarios.md).
- **Sprint 9:** Model Observatory Dashboard — registry UI, model detail page, ML performance viz, comparison/ranking, tuning, lifecycle controls, drift/health UI, HITL review mode, sandbox/what-if. See [SPRINT-9-COMPLETE.md](SPRINT-9-COMPLETE.md), [SPRINT-9-IMPLEMENTATION-GUIDE.md](SPRINT-9-IMPLEMENTATION-GUIDE.md).
- **Full index:** [SPRINTS-7-8-9-SUMMARY.md](SPRINTS-7-8-9-SUMMARY.md).

#### Sprint 10: Polymarket BTC hourly market-making ✅
- **Purpose:** Optional **parallel trading surface** — prediction-market (CLOB) market making on Polymarket hourly BTC Up/Down markets. Shares **Postgres/TimescaleDB** with Caliper for unified analytics; **does not** use `packages/strategies` or Alpaca `execution` OMS (intentional separation; see spec).
- **Service** (`services/polymarket/`): Gamma + CLOB + Binance + Data API clients; Polygon wallet (EIP-712); fixed-spread V1 quoting; post-only + heartbeat; safety layer; session orchestrator; Typer CLI (`polymarket-session`, `--dry-run`).
- **Data:** Alembic migration `services/data` → `pm.*` schema (sessions, orders, fills, snapshots, candles, PnL, market metadata, toxic flow by minute); telemetry for queue position, adverse selection, reward eligibility, regime tags.
- **API:** `services/api/routers/polymarket.py` + `packages/common/polymarket_schemas.py` (read-oriented session analytics; wiring to live DB per deployment).
- **Docs:** [polymarket-btc-trading-spec.md](plans/specs/polymarket-btc-trading-spec.md) · [SPRINT-10-POLYMARKET-COMPLETE.md](plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md) · [POLYMARKET-QUICKSTART.md](POLYMARKET-QUICKSTART.md) · [runbooks/polymarket-operations.md](runbooks/polymarket-operations.md) · `services/polymarket/docs/`.
- **Roadmap:** Phase 2 (inventory skew, dynamic spread, rewards) and Phase 3 (hybrid directional model) in spec §10 — V1 is data-collection first with dust capital.

#### Sprint 11: Unified architecture (unified pipeline) ✅
- **Purpose:** Single path from signals through allocation, global risk, and market-specific execution adapters (equities vs Polymarket CLOB).
- **Artifacts:** `UnifiedSignal`, `ExecutionAdapter` implementations, `GlobalRiskManager`, `PolymarketMMStrategy` extraction, **`services/portfolio/`** (allocator utilities).
- **Plan:** [2026-04-04-unified-architecture-refactor.md](plans/2026-04-04-unified-architecture-refactor.md) · **Progress:** [PROGRESS.md](plans/PROGRESS.md) (v2.1.0).

#### Sprint 12: Feature layer unification ✅
- **Purpose:** One **feature contract** for Polymarket research and runtime: four families (market state, microstructure, probabilistic, regime), persisted snapshots, API exposure.
- **Artifacts:** **`FeatureSnapshot`** / **`FeatureRecord`**, **`CLOBSource`** / **`BinanceSource`**, **`FeatureBuilder`**, **`pm.features`**, feature store + session/API integration.
- **Spec / tickets:** [sprint-12-feature-layer-spec.md](plans/specs/sprint-12-feature-layer-spec.md) · [12-00-INDEX.md](plans/tickets/12-00-INDEX.md).

#### Sprint 13: Simulation + evaluation engine ✅
- **Purpose:** **Offline** CLOB replay and post-run evaluation (does **not** replace **`services/backtest/`** for equity).
- **Artifacts:** **`services/simulation/`** (schemas, order book, fees, execution simulator, adverse selection, loader, replay engine, runner, validation), **`services/evaluation/`** (metrics, baselines, regime matrix, reports), Alembic **`004_*`**, **`/v1/simulation/*`** and **`/v1/evaluation/*`** (stub-backed until DB + runner wiring).
- **Spec / tickets / summary:** [sprint-13-simulation-evaluation-spec.md](plans/specs/sprint-13-simulation-evaluation-spec.md) · [13-00-INDEX.md](plans/tickets/13-00-INDEX.md) · [SPRINT-13-SIMULATION-EVALUATION.md](plans/summaries/SPRINT-13-SIMULATION-EVALUATION.md).

#### Sprint 14: BTC probability model ✅ (library + API + migration; **tests incomplete**)
- **Purpose:** Calibrated **`p_hat(t)`** for hourly BTC Up/Down, lead-lag vs Polymarket implied prob, fee-aware backtest, drift on calibration.
- **Artifacts:** **`services/ml/probability_model/`** (dataset, trainer, GBT/registry, lag tests, backtest, predictor, drift), Alembic **`005_*`**, **`/v1/probability/*`** (contract stubs/mocks on several routes until wired to DB).
- **Deferred:** Spec **AC-9** — no dedicated pytest suite yet (**14-11** in [14-00-INDEX.md](plans/tickets/14-00-INDEX.md)).
- **Spec / summary:** [sprint-14-probability-model-spec.md](plans/specs/sprint-14-probability-model-spec.md) · [SPRINT-14-PROBABILITY-MODEL.md](plans/summaries/SPRINT-14-PROBABILITY-MODEL.md).

#### Sprint 15: Regime detection + dynamic allocation ✅
- **Purpose:** Global and per-market regime labels, rolling performance matrix, HRP-style capital allocation for the Polymarket research stack.
- **Artifacts:** **`services/regime/`**, **`services/allocation/`**, Alembic **`006_create_regime_allocation_tables.py`** (`pm.regime_states`, `pm.allocation_decisions`, `pm.performance_matrices`), **`/v1/regime/*`**, **`/v1/allocation/*`** — **live DB reads** when **`DB_URL`** is set.
- **Spec / tickets:** [sprint-15-regime-allocation-spec.md](plans/specs/sprint-15-regime-allocation-spec.md) · [15-00-INDEX.md](plans/tickets/15-00-INDEX.md).

#### Sprint 16: Cross-sectional ranking + model fleet ✅
- **Purpose:** Rank hourly BTC (and related) markets cross-sectionally; run a **paper-mode** multi-strategy fleet with persisted paper fills.
- **Artifacts:** **`services/ranking/`** (universe, edge, feasibility, scoring, selection + cooldown), **`services/fleet/`** (orchestrator, **`PaperTradeStore`**, **`pm.paper_trades`**), Alembic **`007_create_pm_paper_trades_table.py`**, fleet strategies in **`packages/strategies/`** (`poly_*_v1`, `poly_mm_v2`), dashboard **`apps/dashboard/src/components/sprint-16/`**.
- **API caveat:** **`GET /v1/ranking/current`**, **`/v1/fleet/*`** require **`DB_URL`** but return **fixed mock JSON** until handlers call **`MarketRanker`**, **`PaperTradeStore`**, and orchestrator state — see [api-contracts.md](api-contracts.md).
- **Spec / tickets:** [sprint-16-cross-sectional-fleet-spec.md](plans/specs/sprint-16-cross-sectional-fleet-spec.md) · [16-00-INDEX.md](plans/tickets/16-00-INDEX.md).

---

## 📊 Feature Details

### Data Ingestion

**Capabilities:**
- Historical data fetching from Alpaca API
- IEX data feed support (free tier)
- Database storage with TimescaleDB
- Data validation and normalization
- Time-series optimized storage (hypertables)

**Supported Data Types:**
- OHLCV price bars (stocks)
- Multiple timeframes (1min, 1hour, 1day)
- Options quotes (schema ready, provider pending)

**Limitations:**
- Currently supports Alpaca provider only
- Free tier limited to IEX feed (~250 trading days)
- Options data ingestion not yet implemented

---

### Feature Engineering

**Technical Indicators:**
1. **SMA** - Simple Moving Average (configurable periods)
2. **EMA** - Exponential Moving Average (configurable periods)
3. **RSI** - Relative Strength Index (default 14-period)
4. **MACD** - Moving Average Convergence Divergence (12, 26, 9)
5. **Bollinger Bands** - Upper, middle, lower bands (20-period, 2 std dev)
6. **ATR** - Average True Range (14-period)
7. **Stochastic Oscillator** - %K and %D (14-period)

**Derived Features:**
- Price returns (1-day, 5-day, 20-day)
- Volatility measures
- Crossover signals
- Price momentum indicators
- Volume-based features

**Total Features:** 30+ computed features per bar

---

### Strategy Framework

**Strategy Interface:**
- Abstract base class with lifecycle hooks
- Signal generation interface
- Portfolio state management
- Risk checking hooks
- Order generation support

**Implemented Strategies:**
1. **SMA Crossover** - Momentum strategy
   - Golden cross (buy signal)
   - Death cross (sell signal)
   - Configurable periods (default: 20/50)
   - Position sizing (default: 10% equity)
2. **Polymarket / unified pipeline** — Sprint 11+ plugins (e.g. market-making extraction) and **Sprint 16 fleet** strategies (`poly_mm_v2`, `poly_regime_v1`, directional and microstructure variants) for paper-mode orchestration under **`services/fleet/`**.

**Strategy Configuration:**
- YAML-based configuration files
- Runtime parameter adjustment
- Strategy-specific settings

**Known Issues:**
- SMA Crossover has Decimal/float type mismatch at line 168 (non-blocking, documented)

---

### Backtesting Engine

**Core Capabilities:**
- Execute any strategy implementing Strategy interface
- Realistic fill simulation
- Commission and slippage modeling
- Position tracking
- Equity curve generation
- Performance metrics calculation

**Fill Simulation:**
- Market orders only (limit/stop orders pending)
- Configurable slippage (default: 10 bps)
- Configurable commission (default: $1.00 per trade)
- Realistic price fills based on bar data

**Performance Metrics:**
- Return metrics (total return, return %)
- Risk metrics (Sharpe ratio, max drawdown)
- Trade statistics (win rate, profit factor, avg win/loss)
- Equity curve data points

**Walk-Forward Optimization:**
- Rolling window optimization
- Anchored window optimization
- Parameter grid search
- Multiple optimization objectives
- Parameter stability analysis
- Out-of-sample performance aggregation

**Report Formats:**
- JSON (machine-readable, API-ready)
- HTML (human-readable with interactive charts)
- Plotly-based visualizations
- Trade-by-trade breakdown

---

## 🧪 Testing & Quality Assurance

### Test Coverage

**Unit Tests:**
- Backtest engine: 20+ tests
- P&L calculation: 15+ tests
- Report generation: 25+ tests
- Feature indicators: Comprehensive tests
- Strategy logic: Signal generation tests

**Integration Tests:**
- Full SMA Crossover backtest workflow
- End-to-end verification
- Known-good scenario validation

**Test Infrastructure:**
- pytest test framework
- Comprehensive test fixtures
- Mock data generators
- Verification runbooks

---

## 📚 Documentation

### Core Documentation
- **README** (`README.md`) — Platform overview, two-track (equities / Polymarket), sprint status
- **Doc index** (`docs/INDEX.md`) — Navigation map
- **Progress log** (`docs/plans/PROGRESS.md`) — Milestones, patches, backlog
- **Architecture** (`docs/architecture.md`) — System design and component overview
- **Data Contracts** (`docs/data-contracts.md`) — Schema definitions (incl. `pm.*` pointer)
- **API Contracts** (`docs/api-contracts.md`) — API specifications (incl. Polymarket routes)
- **Risk Policy** (`docs/risk-policy.md`) — Risk management rules (equity path)
- **Security** (`docs/security.md`) — Security policies

### Implementation Documentation
- **Sprint Summaries** - Detailed sprint completion reports (including `docs/SPRINT-8-COMPLETE.md`, `docs/SPRINT-9-COMPLETE.md`)
- **Sprints 7–9 Summary** - [docs/SPRINTS-7-8-9-SUMMARY.md](SPRINTS-7-8-9-SUMMARY.md) — Single entry point for Sprints 7–9 documentation and implementation
- **ADRs** - Architecture Decision Records (5 ADRs)
- **Runbooks** - Verification and troubleshooting guides (including `docs/runbooks/stress-scenarios.md` for Sprint 8)
- **Service READMEs** - Per-service documentation

### Multi-Agent Workflow
- **Workflow Guide** (`docs/workflow/WORKFLOW.md`) - Multi-agent development protocol
- **Agent Briefs** (`agents/briefs/`) - Role-specific instructions
- **Sprint Prompts** (`docs/workflow/`) - Agent prompts for Sprints 3-4

---

## 🔄 Data Flow

### Equities workflow (Sprints 1–9)

```
1. Data (Sprint 1)     AlpacaProvider → TimescaleDB (price bars)
2. Features (Sprint 2) Price bars → FeaturePipeline → indicators / 30+ features
3. Strategy (Sprint 2+) Signals from rule strategies (e.g. SMA) or ML (Sprint 7+)
4. Backtest (Sprint 3) BacktestEngine → metrics, reports (JSON/HTML)
5. API + Dashboard (Sprints 4, 9) FastAPI ↔ Next.js (runs, health, Model Observatory)
6. Risk + Execution (Sprint 5) RiskManager → OMS → Alpaca (paper first)
7. ML safety (Sprints 6–8) Drift, gating, explainability, baselines, HITL, performance APIs
```

### Polymarket workflow (Sprint 10, optional)

```
Gamma/CLOB/Binance → services/polymarket (discovery, feed, quoting, safety)
                    → Polygon CLOB (post-only orders)
                    → pm.* TimescaleDB (recorder)
                    → GET /v1/polymarket/* (API) for session analytics
(Does not use equity Strategy / execution / risk stack.)
```

---

## Sprint completion reference (historical checklist)

### Sprint 5: Execution & Risk ✅ COMPLETE
- ✅ Paper trading execution (Alpaca Paper API)
- ✅ Risk management module (RiskManager)
- ✅ Circuit breakers and kill switches
- ✅ Order Management System (OMS)
- ✅ Position tracking and reconciliation
- ✅ 114 tests (76 unit + 38 integration)

### Sprint 6: ML Safety & Interpretability ✅ COMPLETE
- ✅ Model drift detection (PSI, KL divergence, health score)
- ✅ Confidence gating and abstention logic (ABSTAIN signal)
- ✅ SHAP integration for explainability
- ✅ Human-in-the-loop controls (approval queue)
- ✅ Regret and baseline comparison metrics
- ✅ Educational tooltips and help page
- ✅ Vercel deployment configuration
- ✅ 70+ tests (unit + integration)

### Sprint 7: First ML Model (End-to-End Loop) ✅ COMPLETE
- ✅ ML problem definition (binary next-bar direction; see `docs/sprint-7-ml-problem-definition.md`)
- ✅ Offline training pipeline (time-aware split, leakage prevention; see `docs/training-first-model.md`)
- ✅ Model interface contract (ModelInput, ModelPrediction, ModelInferenceOutput; see `docs/model-interface-contract.md`)
- ✅ Inference integration (MLDirectionStrategyV1, confidence gating, prediction logging; see `docs/sprint-7-inference-and-explainability.md`, `docs/using-ml-strategy.md`)
- ✅ Text-based explainability (SimpleExplainer, stored with predictions)

### Sprint 8: ML Observability, Safety & Evaluation ✅ COMPLETE
- ✅ Performance tracking (prediction vs outcome, rolling accuracy, abstention rate; API `GET /v1/metrics/performance/{model_id}`)
- ✅ Baseline & regret wiring (regret vs hold cash, buy & hold, random; API `GET /v1/baselines/comparison`)
- ✅ Drift monitoring (reference + current distributions, health score; API drift/metrics, drift/health)
- ✅ SHAP/permutation explainability per prediction (API `GET /v1/explanations/{trade_id}`)
- ✅ Stress scenarios runbook and simulation scripts (`docs/runbooks/stress-scenarios.md`, `tests/stress/`)

### Sprint 9: Model Observatory Dashboard ✅ COMPLETE
- ✅ Model Registry UI (`/models` — list view, sorting/filtering, quick actions)
- ✅ Model Detail page (`/models/[id]` — overview, training summary, performance, health)
- ✅ ML performance visualization (rolling accuracy, confidence; advanced charts extendable)
- ✅ Model comparison & ranking (infrastructure and API support)
- ✅ Hyperparameter & threshold tuning (API, confirmation, logging)
- ✅ Model lifecycle controls (activate, pause, retire, promote, clone)
- ✅ Drift & health visualization UI
- ✅ HITL review mode (model-centric)
- ✅ Model sandbox / what-if (parameter sandbox, preview)

**Sprints 7–9 summary:** See [docs/SPRINTS-7-8-9-SUMMARY.md](SPRINTS-7-8-9-SUMMARY.md) for full documentation index and implementation details.

### Sprint 10: Polymarket BTC hourly market-making ✅ COMPLETE
- ✅ Parallel service `services/polymarket/` with CLI, adapters, wallet, recorder, integration tests
- ✅ `pm.*` TimescaleDB schema and migration (`services/data`)
- ✅ V1 market-making (fixed spread, post-only, session safety limits, rich `pm.*` telemetry)
- ✅ FastAPI Polymarket router + shared Pydantic schemas (`packages/common/polymarket_schemas.py`)
- ✅ Operations docs: [POLYMARKET-QUICKSTART.md](POLYMARKET-QUICKSTART.md), [runbooks/polymarket-operations.md](runbooks/polymarket-operations.md)

### Sprint 11: Unified pipeline ✅ COMPLETE
- ✅ `UnifiedSignal` → portfolio allocator → `GlobalRiskManager` → `ExecutionAdapter` (equity vs Polymarket)
- ✅ `services/portfolio/` and Polymarket MM logic as a strategy plugin where applicable

### Sprint 12: Feature layer ✅ COMPLETE
- ✅ `FeatureSnapshot` contract and `pm.features` persistence
- ✅ CLOB + Binance sources, feature builder, feature store, session/API hooks per [12-00-INDEX.md](plans/tickets/12-00-INDEX.md)

### Sprint 13: Simulation + evaluation ✅ COMPLETE
- ✅ `services/simulation/` replay stack + unit tests; `services/evaluation/` metrics/baselines + tests
- ✅ `004_create_simulation_evaluation_tables.py`; integration tests under `tests/integration/simulation/`
- ✅ FastAPI routes under `/v1/simulation/*` and `/v1/evaluation/*` (contract-complete stubs)

### Sprint 14: BTC probability model ✅ COMPLETE (tests **open**)
- ✅ `services/ml/probability_model/` — panel builder, trainers, lag tests, fee-aware backtest, predictor, drift monitor
- ✅ `005_create_probability_model_tables.py`; `/v1/probability/*` router
- ⏳ Spec **AC-9** unit + integration tests — **not implemented** (see [14-00-INDEX.md](plans/tickets/14-00-INDEX.md))

### Sprint 15: Regime + allocation ✅ COMPLETE
- ✅ `services/regime/`, `services/allocation/`; `006_create_regime_allocation_tables.py`
- ✅ `/v1/regime/*`, `/v1/allocation/*` — live reads from `pm.*` when `DB_URL` set

### Sprint 16: Ranking + fleet ✅ COMPLETE (HTTP mock for ranker/fleet reads)
- ✅ `services/ranking/`, `services/fleet/`; `007_create_pm_paper_trades_table.py`; fleet strategies; dashboard `sprint-16` components
- ⏳ Wire `/v1/ranking/*` and `/v1/fleet/*` to ranker, `PaperTradeStore`, orchestrator — see [api-contracts.md](api-contracts.md)

### Future Enhancements
- Polymarket Phase 2+ per [polymarket-btc-trading-spec.md](plans/specs/polymarket-btc-trading-spec.md) (inventory skew, dynamic spread, hybrid directional model, deeper dashboard integration)
- Multi-asset portfolio backtesting
- Limit/stop order simulation
- Monte Carlo simulation
- Advanced slippage models
- Options data ingestion and strategy surfaces (schemas partially ready)
- Additional production model families (e.g. XGBoost/LightGBM) beyond the first sklearn path
- Real-time data streaming
- WebSocket support for dashboard

---

## 📈 Metrics & Statistics

### Codebase Statistics
- **Total Lines of Code:** ~10,000+ lines (excluding later service additions)
- **Services:** Core: data, features, backtest, api, execution, risk, ml; **Polymarket / research:** `polymarket`, `simulation`, `evaluation`, `portfolio`, `regime`, `allocation`, `ranking`, `fleet` (see [PROGRESS.md](plans/PROGRESS.md))
- **Packages:** `common`, `strategies` (active); `models` (stub)
- **Test Coverage:** 370+ core tests; additional tests under `tests/unit/polymarket/`, `tests/integration/polymarket/`, `tests/unit/simulation/`, `tests/unit/evaluation/`, `tests/integration/simulation/`
- **Documentation:** 20+ major documents plus Polymarket spec, summary, quickstart, and operations runbook
- **ADRs:** 7 architecture decision records

### Sprint Completion
- **Sprint 1:** ✅ Complete (Infrastructure & Data)
- **Sprint 2:** ✅ Complete (Feature Pipeline & Strategy Core)
- **Sprint 3:** ✅ Complete (Backtesting & Reporting)
- **Sprint 4:** ✅ Complete (Dashboard & API)
- **Sprint 5:** ✅ Complete (Execution & Risk)
- **Sprint 6:** ✅ Complete (ML Safety & Interpretability)
- **Sprint 7:** ✅ Complete (First ML Model – End-to-End Loop)
- **Sprint 8:** ✅ Complete (ML Observability, Safety & Evaluation)
- **Sprint 9:** ✅ Complete (Model Observatory Dashboard)
- **Sprint 10:** ✅ Complete (Polymarket BTC hourly market-making — `services/polymarket/`)
- **Sprint 11:** ✅ Complete (unified pipeline — `services/portfolio/`, adapters, global risk)
- **Sprint 12:** ✅ Complete (feature layer — `FeatureSnapshot`, `pm.features`, sources, store)
- **Sprint 13:** ✅ Complete (simulation + evaluation — `services/simulation/`, `services/evaluation/`)
- **Sprint 14:** ✅ Complete (probability model — `services/ml/probability_model/`); **AC-9 tests pending**
- **Sprint 15:** ✅ Complete (regime + allocation — `services/regime/`, `services/allocation/`)
- **Sprint 16:** ✅ Complete (ranking + fleet — `services/ranking/`, `services/fleet/`); **ranking/fleet REST still mock**

---

## 🐛 Known Issues

1. **Sprint 14 — AC-9 test suite not landed** — Library, migration, and `/v1/probability/*` router are merged; dedicated unit + integration tests per spec remain to be added ([14-00-INDEX.md](plans/tickets/14-00-INDEX.md) task **14-11**).

2. **Sprint 16 — ranking/fleet API not wired to live services** — `GET /v1/ranking/current` and `/v1/fleet/*` return static mock payloads for contract/dashboard coverage; libraries and `pm.paper_trades` writes exist — see [api-contracts.md](api-contracts.md) and [PROGRESS.md](plans/PROGRESS.md) backlog.

3. **SMA Crossover Strategy Type Mismatch** (Non-blocking)
   - Location: `packages/strategies/sma_crossover.py:168`
   - Issue: Decimal / float operation causing type mismatch
   - Impact: One integration test marked `xfail`
   - Status: Documented, can be fixed in future sprint

---

## 🔗 Related Documentation

- [User guide](user-guide.md) — install, `DB_URL`, run API and dashboard, equities vs Polymarket
- [Architecture Overview](architecture.md)
- [Sprint 3 Summary](plans/summaries/SPRINT3_SUMMARY.md)
- [Sprint 4 Summary](plans/summaries/SPRINT4_SUMMARY.md)
- [Sprint 5 Summary](plans/summaries/SPRINT5_SUMMARY.md)
- [Sprint 6 Summary](plans/summaries/SPRINT6_SUMMARY.md)
- [Backtest Verification Runbook](runbooks/backtest-verification.md)
- [ML Safety Verification Runbook](runbooks/ml-safety-verification.md)
- [Execution Verification Runbook](runbooks/execution-verification.md)
- [Polymarket Operations Runbook](runbooks/polymarket-operations.md)
- [Sprint 10 summary](plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md)
- [Sprint 13 summary](plans/summaries/SPRINT-13-SIMULATION-EVALUATION.md)
- [Sprint 14 summary](plans/summaries/SPRINT-14-PROBABILITY-MODEL.md)
- [Multi-Agent Workflow](workflow/WORKFLOW.md)

---

**Last Updated:** 2026-04-06  
**Maintained By:** Development Team
