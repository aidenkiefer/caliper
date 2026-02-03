# Progress Tracker

## Current Phase: Implementation - Sprints 7–9 ✅ COMPLETE

**Last Updated:** 2026-02-02

**Completed:** Sprints 1-9 (Infrastructure through Model Observatory Dashboard)  
**Current:** None (all planned sprints complete)  
**Next Up:** Iteration on Sprints 7–9 (see [docs/SPRINTS-7-8-9-SUMMARY.md](../docs/SPRINTS-7-8-9-SUMMARY.md))

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

### Sprint 7: First ML Model (End-to-End Loop) - ✅ COMPLETE
*Goal: Introduce exactly one real ML model into the system and run it end-to-end with correct training, validation, inference, and execution semantics.*

**7.1 ML Problem Definition**
- [x] Define target variable (e.g. probability of positive return over next N bars)
- [x] Define prediction horizon and label construction logic
- [x] Define evaluation metrics (classification or regression)
- [x] Document assumptions and failure modes
- [x] **Verification:** Model target and metrics clearly documented

**7.2 Training & Validation Pipeline**
- [x] Implement offline training script
- [x] Time-aware train/validation split (walk-forward or sliding window)
- [x] Explicit data leakage prevention (e.g. no future data in features)
- [x] Log training and validation metrics
- [x] **Verification:** Training run reproducible and metrics logged

**7.3 Model Interface & Contract**
- [x] Standardized model input schema (features, symbol, timestamp)
- [x] Standardized output schema: prediction, confidence, abstain signal
- [x] Explicit confidence semantics (e.g. 0–1, when to ABSTAIN)
- [x] **Verification:** Execution layer can consume model output unambiguously

**7.4 Inference Integration**
- [x] Run model inference in the live/paper pipeline (strategy or dedicated service)
- [x] Integrate model output with existing risk and execution layers
- [x] Log predictions, confidence, and decisions (e.g. to DB or structured logs)
- [x] **Verification:** Model predictions flow through full system (data → model → signal → risk → order)

**7.5 Text-Based Explainability (Initial)**
- [x] Simple explanation payload (features used, confidence, short rationale)
- [x] Store explanations alongside predictions/trades
- [x] **Verification:** Each prediction has a human-readable explanation (no SHAP required yet)

### Sprint 8: ML Observability, Safety & Evaluation - ✅ COMPLETE
*Goal: Make the first ML model observable, debuggable, and safe before scaling to multiple models.*

**8.1 Model Performance Tracking**
- [x] Log prediction vs outcome (direction or return) when ground truth is available
- [x] Compute rolling accuracy / error metrics (e.g. over last N days)
- [x] Track abstention rate over time
- [x] Expose performance metrics via API or DB for dashboard
- [x] **Verification:** Performance queryable per model over time

**8.2 Baseline & Regret Metrics**
- [x] Wire existing baselines (hold cash, buy & hold, random) to model strategy comparison
- [x] Compute regret (strategy vs baselines) for the live model
- [x] Store and expose regret metrics (e.g. API or dashboard feed)
- [x] **Verification:** Model performance contextualized vs baselines

**8.3 Confidence & Drift Monitoring**
- [x] Feed current feature (and confidence) distributions into existing drift detector
- [x] Store reference (training) distributions for comparison
- [x] Compute and store health score from drift signals
- [x] Expose drift metrics and health via API (e.g. per model, per feature)
- [x] **Verification:** Drift metrics stored and queryable per model

**8.4 Explainability (Advanced)**
- [x] Integrate SHAP (or permutation importance) for the deployed model’s predictions
- [x] Store explanation payload per prediction/recommendation
- [x] **Verification:** Explanation available for each recommendation (e.g. via API or trade record)

**8.5 Failure Mode & Stress Simulation**
- [x] Implement or script: missing data simulation (e.g. drop bars, NaN features)
- [x] Implement or script: volatility spike simulation (e.g. scaled returns)
- [x] Implement or script: API outage simulation (e.g. broker unavailable)
- [x] Document system behavior under each scenario (no trade, abstain, fallback, etc.)
- [x] **Verification:** Failure modes are understood and documented (runbook or ADR)

### Sprint 9: Model Observatory Dashboard - ✅ COMPLETE
*Goal: Make models inspectable, configurable, and comparable as first-class entities in the dashboard.*

**9.1 Model Registry UI**
- [x] Dedicated Model Registry page in dashboard
- [x] List view with sorting/filtering
- [x] Display: name, type, status, trained date, health score, allocation weight
- [x] Quick actions (activate, pause, view details)
- [x] **Verification:** All models visible in dashboard list

**9.2 Model Detail Page**
- [x] Model overview section (architecture, feature set, hyperparams)
- [x] Training & validation summary (period, method, metrics, overfitting indicators)
- [x] Live/paper performance (accuracy over time, abstention rate)
- [x] Confidence calibration plots
- [x] **Verification:** Full model context visible on single page

**9.3 ML Performance Visualization**
- [x] Prediction vs actual plots (directional or regression)
- [x] Rolling accuracy charts
- [x] Confusion matrix (for classification)
- [x] Calibration curves (confidence vs correctness)
- [x] Error distribution plots
- [x] Toggle between ML metrics and trading metrics
- [x] **Verification:** ML-native visualizations render correctly

**9.4 Model Comparison & Ranking View**
- [x] Side-by-side model comparison page
- [x] Comparison dimensions: validation metrics, recent performance, drawdown, volatility
- [x] Sorting/filtering (best performers, most stable, least risky)
- [x] Confidence stability and drift score comparison
- [x] **Verification:** Can rank models by multiple criteria

**9.5 Hyperparameter & Threshold Tuning Interface**
- [x] Dashboard controls for confidence thresholds
- [x] Abstention threshold adjustment
- [x] Ensemble contribution caps
- [x] Allocation limit controls
- [x] Change confirmation modal with impact preview
- [x] Change logging and rollback support
- [x] **Verification:** Parameter changes reflected in model behavior

**9.6 Model Lifecycle Controls**
- [x] Activate / deactivate model from dashboard
- [x] Promote candidate → active workflow
- [x] Retire model action
- [x] Freeze parameters toggle
- [x] Clone model config for new experiment
- [x] **Verification:** Lifecycle actions update model state correctly

**9.7 Model Drift & Health Visualization UI**
- [x] Per-model drift trend charts
- [x] Feature drift heatmaps
- [x] Health score timeline
- [x] Alert badges and threshold indicators
- [x] Suggested actions (retrain, retire)
- [x] **Verification:** Drift aging is visible, not silent

**9.8 Human-in-the-Loop Review Mode (Model-Centric)**
- [x] Model recommendation review queue
- [x] Explanation display per recommendation
- [x] Approve/reject at model level
- [x] Rationale input (optional)
- [x] Decision outcome logging
- [x] **Verification:** User can review and decide on model recommendations

**9.9 Model Sandbox / What-If Testing**
- [x] Parameter modification sandbox (no live impact)
- [x] Rerun backtests with modified thresholds
- [x] Temporarily disable models in sandbox
- [x] Compare hypothetical allocations
- [x] Preview effects before applying changes
- [x] **Verification:** Safe experimentation without affecting live behavior

---

## Completed Artifacts

### Planning Documentation
- ✅ `/plans/task_plan.md` - 9-sprint implementation plan
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
| 6 | ML Safety & Interpretability | ✅ Complete |
| 7 | First ML Model (End-to-End Loop) | ✅ Complete |
| 8 | ML Observability, Safety & Evaluation | ✅ Complete |
| 9 | Model Observatory Dashboard | ✅ Complete |

---

## Next Actions

1. ✅ Sprint 3 complete - Backtesting & Reporting implemented
2. ✅ Sprint 4 complete - Dashboard & API implemented
3. ✅ Sprint 5 complete - Execution & Risk implemented
4. ✅ Sprint 6 complete - ML Safety & Interpretability Core
5. ✅ Sprint 7 complete - First ML Model (End-to-End Loop)
6. ✅ Sprint 8 complete - ML Observability, Safety & Evaluation
7. ✅ Sprint 9 complete - Model Observatory Dashboard

---

## Blockers

**None.** All sprints 1–9 complete. See [docs/SPRINTS-7-8-9-SUMMARY.md](../docs/SPRINTS-7-8-9-SUMMARY.md) for documentation index and next steps.
