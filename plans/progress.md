# Progress Tracker

## Current Phase: Implementation - Sprint 6 ✅ COMPLETE

**Last Updated:** 2026-01-26

**Completed:** Sprints 1-6 (Infrastructure, Features, Backtest, Dashboard, Execution & Risk, ML Safety)  
**Current:** Sprint 7 (MLOps & Advanced Analysis)  
**Next Up:** Sprint 8 (Model Observatory Dashboard)

---

## Sprint Status

### Sprint 1: Infrastructure & Data ✅ COMPLETE
- [x] Monorepo structure created
- [x] Docker Compose with TimescaleDB + Redis
- [x] Shared Pydantic schemas (`packages/common/schemas.py`)
- [x] Data service skeleton (`services/data`)
- [x] AlpacaProvider implementation (IEX feed for free tier)
- [x] Alembic migrations with TimescaleDB hypertables
- [x] **Verification:** 250 AAPL bars fetched and stored in database

### Sprint 2: Feature Pipeline & Strategy Core ✅ COMPLETE
- [x] Feature engineering pipeline (`services/features`)
- [x] Technical indicators: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, Stochastic
- [x] Strategy base class (`packages/strategies/base.py`)
- [x] SMA Crossover strategy (`packages/strategies/sma_crossover.py`)
- [x] **Verification:** Compare computed indicators against known values
- [x] **Verification:** Run strategy on dataset and log signals

### Sprint 3: Backtesting & Reporting ✅ COMPLETE
- [x] Backtest engine (`services/backtest/engine.py`)
- [x] Strategy integration with backtest engine
- [x] P&L calculation with accurate math
- [x] Performance metrics (Sharpe, drawdown, win rate, profit factor)
- [x] Report generation (JSON + HTML with Plotly charts)
- [x] Walk-forward optimization engine (bonus feature)
- [x] Unit tests (60+ tests)
- [x] Integration test (SMA Crossover backtest)
- [x] **Verification:** Backtest Starter Strategy, P&L math verified
- [x] Documentation (README, runbook, architecture updates, ADR)

### Sprint 4: Dashboard & API ✅ COMPLETE
- [x] FastAPI backend (`services/api/`)
- [x] 10 REST endpoints per `docs/api-contracts.md`
- [x] Pydantic response models (`packages/common/api_schemas.py`)
- [x] Next.js 14 dashboard (`apps/dashboard/`)
- [x] Overview, Strategies, Runs, Health, Settings pages
- [x] Shadcn/UI components + Tailwind CSS
- [x] API client with SWR hooks
- [x] Dark mode and responsive design
- [x] Docker configuration for API service
- [x] Makefile with dev targets
- [x] 160 tests (135 unit + 25 integration)
- [x] `docs/runbooks/api-verification.md` created
- [x] `adr/0006-api-architecture.md` created
- [x] **Verification:** Backtest results visible in Dashboard

### Sprint 5: Execution & Risk ✅ COMPLETE
- [x] Execution engine (`services/execution`)
- [x] Alpaca broker client integration (`AlpacaClient`)
- [x] Order Management System (OMS) with state machine
- [x] Risk guardrails (`services/risk`)
- [x] Kill switch (global and per-strategy)
- [x] Circuit breaker with auto-triggers
- [x] Position limits and drawdown controls
- [x] API endpoints (`/v1/orders`, `/v1/controls/kill-switch`)
- [x] 114 tests (76 unit + 38 integration)
- [x] Documentation and ADR
- [x] **Verification:** Order rejected when exceeding risk limits

### Sprint 6: ML Safety & Interpretability Core - ✅ COMPLETE
*Goal: Enable explicit model behavior under uncertainty, build trust through interpretability*

**6.1 Model Drift & Decay Detection**
- [x] Feature distribution drift tracking (PSI, KL divergence)
- [x] Prediction confidence drift monitoring
- [x] Error drift tracking (when ground truth available)
- [x] Threshold-based alerts for drift
- [x] Model "health score" derived from drift signals
- [x] **Verification:** Drift metrics queryable per model

**6.2 Confidence Gating & Abstention Logic**
- [x] Extend model output schema to support ABSTAIN signal
- [x] Configurable confidence thresholds per strategy
- [x] Entropy/uncertainty measure calculation
- [x] Ensemble disagreement signals
- [x] Backtest engine support for abstention trades
- [x] **Verification:** Strategy can abstain when confidence < threshold

**6.3 Local Explainability (SHAP)**
- [x] SHAP integration for tree-based models
- [x] Permutation importance fallback
- [x] Explanation payload schema (features, influence, confidence)
- [x] Store explanations alongside trade records
- [x] Dashboard UI for viewing trade explanations
- [x] **Verification:** Each recommendation has human-readable explanation

**6.4 Human-in-the-Loop Controls**
- [x] Approval flag in execution pipeline
- [x] Manual override UI in dashboard
- [x] Recommendation queue (pending human approval)
- [x] Logged human vs model decision comparison
- [x] **Verification:** Trade requires explicit approval when enabled

**6.5 Regret & Baseline Comparison Metrics**
- [x] Baseline strategy implementations (hold cash, buy & hold, random)
- [x] Regret metrics calculation vs baselines
- [x] Track regret over time
- [x] Dashboard visualization of relative performance
- [x] **Verification:** Dashboard shows "vs baseline" comparison

**6.6 Polish & UX (from backlog)**
- [x] Educational tooltips for trading terminology
- [x] Help page with glossary
- [x] Tooltip component for StatsCard and table headers
- [x] Vercel deployment configuration

### Sprint 7: MLOps & Advanced Analysis - Not Started
*Goal: Build operational infrastructure for reproducibility, simulation, and intelligent capital allocation*

**7.1 Feature Registry & Lineage Tracking**
- [ ] Feature registry schema (name, definition, window, source, version)
- [ ] Database table or metadata store
- [ ] Feature versioning support
- [ ] Link features → models → experiments
- [ ] **Verification:** Feature used in model is traceable to definition

**7.2 Experiment Registry & Research Traceability**
- [ ] Experiment registry schema (dataset, features, model, hyperparams, metrics)
- [ ] Deployment status tracking (research → staging → production)
- [ ] Links between experiments, models, and live runs
- [ ] Queryable history of model evolution
- [ ] **Verification:** Can answer "why did we deploy this model?"

**7.3 Model Registry Backend**
- [ ] Model registry API (CRUD for model metadata)
- [ ] Persistent model metadata store
- [ ] Model lifecycle states (active, paused, candidate, retired)
- [ ] Model health score integration (from drift metrics)
- [ ] **Verification:** Model metadata queryable via API

**7.4 Dynamic Capital Allocation**
- [ ] Capital allocation policy module
- [ ] Inputs: recent performance, drawdown, volatility, confidence/drift scores
- [ ] Per-model allocation caps
- [ ] Logged allocation decisions for auditability
- [ ] Integration with ensemble layer
- [ ] **Verification:** Capital shifts away from underperforming models

**7.5 Failure Mode & Stress Simulation**
- [ ] Scenario simulation framework
- [ ] Volatility spike simulation
- [ ] Missing/delayed data simulation
- [ ] Poor fills / increased slippage simulation
- [ ] API outage simulation
- [ ] Partial execution failure simulation
- [ ] Stress-test reports
- [ ] Documented failure handling strategies
- [ ] **Verification:** System behavior documented under adverse conditions

**7.6 Model Drift & Health Visualization API**
- [ ] API endpoints for drift metrics per model
- [ ] Feature drift over time data
- [ ] Confidence drift data
- [ ] Health score trend data
- [ ] Alert thresholds and suggested actions
- [ ] **Verification:** Drift visualization data available via API

### Sprint 8: Model Observatory Dashboard - Not Started
*Goal: Make models inspectable, configurable, and comparable as first-class entities*

**8.1 Model Registry UI**
- [ ] Dedicated Model Registry page in dashboard
- [ ] List view with sorting/filtering
- [ ] Display: name, type, status, trained date, health score, allocation weight
- [ ] Quick actions (activate, pause, view details)
- [ ] **Verification:** All models visible in dashboard list

**8.2 Model Detail Page**
- [ ] Model overview section (architecture, feature set, hyperparams)
- [ ] Training & validation summary (period, method, metrics, overfitting indicators)
- [ ] Live/paper performance (accuracy over time, abstention rate)
- [ ] Confidence calibration plots
- [ ] **Verification:** Full model context visible on single page

**8.3 ML Performance Visualization**
- [ ] Prediction vs actual plots (directional or regression)
- [ ] Rolling accuracy charts
- [ ] Confusion matrix (for classification)
- [ ] Calibration curves (confidence vs correctness)
- [ ] Error distribution plots
- [ ] Toggle between ML metrics and trading metrics
- [ ] **Verification:** ML-native visualizations render correctly

**8.4 Model Comparison & Ranking View**
- [ ] Side-by-side model comparison page
- [ ] Comparison dimensions: validation metrics, recent performance, drawdown, volatility
- [ ] Sorting/filtering (best performers, most stable, least risky)
- [ ] Confidence stability and drift score comparison
- [ ] **Verification:** Can rank models by multiple criteria

**8.5 Hyperparameter & Threshold Tuning Interface**
- [ ] Dashboard controls for confidence thresholds
- [ ] Abstention threshold adjustment
- [ ] Ensemble contribution caps
- [ ] Allocation limit controls
- [ ] Change confirmation modal with impact preview
- [ ] Change logging and rollback support
- [ ] **Verification:** Parameter changes reflected in model behavior

**8.6 Model Lifecycle Controls**
- [ ] Activate / deactivate model from dashboard
- [ ] Promote candidate → active workflow
- [ ] Retire model action
- [ ] Freeze parameters toggle
- [ ] Clone model config for new experiment
- [ ] **Verification:** Lifecycle actions update model state correctly

**8.7 Model Drift & Health Visualization UI**
- [ ] Per-model drift trend charts
- [ ] Feature drift heatmaps
- [ ] Health score timeline
- [ ] Alert badges and threshold indicators
- [ ] Suggested actions (retrain, retire)
- [ ] **Verification:** Drift aging is visible, not silent

**8.8 Human-in-the-Loop Review Mode (Model-Centric)**
- [ ] Model recommendation review queue
- [ ] Explanation display per recommendation
- [ ] Approve/reject at model level
- [ ] Rationale input (optional)
- [ ] Decision outcome logging
- [ ] **Verification:** User can review and decide on model recommendations

**8.9 Model Sandbox / What-If Testing**
- [ ] Parameter modification sandbox (no live impact)
- [ ] Rerun backtests with modified thresholds
- [ ] Temporarily disable models in sandbox
- [ ] Compare hypothetical allocations
- [ ] Preview effects before applying changes
- [ ] **Verification:** Safe experimentation without affecting live behavior

---

## Completed Artifacts

### Planning Documentation
- ✅ `/plans/task_plan.md` - 8-sprint implementation plan
- ✅ `/plans/findings.md` - Research insights and decisions
- ✅ `/plans/progress.md` - This file
- ✅ `/plans/milestones.md` - Project milestones

### Technical Documentation
- ✅ `/docs/architecture.md` - System architecture
- ✅ `/docs/data-contracts.md` - Canonical schemas
- ✅ `/docs/api-contracts.md` - FastAPI endpoints
- ✅ `/docs/security.md` - Secrets and security
- ✅ `/docs/risk-policy.md` - Risk limits and kill switches
- ✅ `/docs/dashboard-spec.md` - Next.js UI/UX spec

### Implementation Documentation (in `plans/`)
- ✅ `plans/SPRINT1_SUMMARY.md` - Sprint 1 deliverables
- ✅ `plans/SPRINT2_SUMMARY.md` - Sprint 2 deliverables
- ✅ `plans/SPRINT3_SUMMARY.md` - Sprint 3 deliverables
- ✅ `plans/SPRINT4_SUMMARY.md` - Sprint 4 deliverables
- ✅ `plans/SPRINT5_SUMMARY.md` - Sprint 5 deliverables
- ✅ `plans/SPRINT_SKILL_OPTIMIZATIONS.md` - Skills-based improvements

### Workflow Documentation (in `docs/workflow/`)
- ✅ `docs/workflow/WORKFLOW.md` - Multi-agent protocol
- ✅ `docs/workflow/MULTI_AGENT_SETUP.md` - Setup guide
- ✅ `docs/workflow/sprint-3-multi.md` - Sprint 3 workflow
- ✅ `docs/workflow/sprint-4-multi.md` - Sprint 4 workflow
- ✅ `docs/workflow/sprint-5-multi.md` - Sprint 5 workflow

---

## Key Fixes Applied During Sprint 1

| Issue | Resolution |
|-------|------------|
| TimescaleDB unique constraints | Added `timestamp` to composite PKs and unique constraints |
| PostgreSQL reserved word `right` | Quoted column in CHECK constraint |
| Poetry package-mode error | Added `package-mode = false` to pyproject.toml |
| Alpaca SDK imports | Changed from `alpaca-trade-api` to `alpaca-py` |
| Alpaca SIP data restriction | Added `feed=DataFeed.IEX` for free tier accounts |
| Monorepo imports | Added project root to `sys.path` in main.py |
| Pydantic validator error | Removed non-existent `timestamp` field from Order validator |

---

## Sprint Roadmap Summary

| Sprint | Focus | Status |
|--------|-------|--------|
| 1 | Infrastructure & Data | ✅ Complete |
| 2 | Feature Pipeline & Strategy Core | ✅ Complete |
| 3 | Backtesting & Reporting | ✅ Complete |
| 4 | Dashboard & API | ✅ Complete |
| 5 | Execution & Risk | ✅ Complete |
| 6 | ML Safety & Interpretability | In Progress |
| 7 | MLOps & Advanced Analysis | Not Started |
| 8 | Model Observatory Dashboard | Not Started |

---

## Next Actions

1. ✅ Sprint 3 complete - Backtesting & Reporting implemented
2. ✅ Sprint 4 complete - Dashboard & API implemented
3. ✅ Sprint 5 complete - Execution & Risk implemented
4. **Current:** Sprint 6 - ML Safety & Interpretability Core
5. **Next:** Sprint 7 - MLOps & Advanced Analysis (backend/infrastructure)
6. **Then:** Sprint 8 - Model Observatory Dashboard (model-centric UI)

---

## Blockers

**None.** Sprint 5 is complete and ready for Sprint 6.
