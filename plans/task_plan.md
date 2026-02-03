# Caliper - Task Plan

## Overview
This document outlines the planning phase deliverables for building a quantitative ML trading platform. This is a **planning and system design** task only - no implementation code will be written.

## Planning Objectives
1. Define comprehensive architecture for trading platform
2. Establish data contracts and schemas
3. Specify API contracts and security policies
4. Design agent systems and tool definitions
5. Plan dashboard UI/UX

## Specialist Agent Coordination

### 🧠 Agent A — Architecture Lead
**Status:** ✅ Complete  
**Deliverable:** `docs/architecture.md`  
**Focus:**
- System components and boundaries  
- Data flow between services
- Service separation (data, features, backtest, execution, risk, monitoring)
- Deployment topology

### 🗄️ Agent B — Data & DB Lead
**Status:** ✅ Complete  
**Deliverable:** `docs/data-contracts.md`  
**Focus:**
- Price bar (OHLCV) schema
- Options quote schema
- Trade & position schemas
- Database design (Postgres + object storage)
- Data versioning and lifecycle

### 🔐 Agent C — API & Security Lead
**Status:** ✅ Complete  
**Deliverables:** `docs/api-contracts.md`, `docs/security.md`  
**Focus:**
- FastAPI backend endpoints
- Authentication boundaries
- Secrets handling (broker APIs, keys)
- Rate limits and circuit breakers

### 🤖 Agent D — Agent Systems Lead
**Status:** ✅ Complete  
**Deliverable:** Tool definitions in `docs/architecture.md`  
**Focus:**
- Agent roles (Data Agent, Strategy Agent, Risk Agent, etc.)
- Tool schemas for ML model execution
- Memory strategy for agent state
- Human-in-the-loop checkpoints (paper trading approval, risk limits)

### 📊 Agent E — Dashboard Planning Lead
**Status:** ✅ Complete  
**Deliverable:** `docs/dashboard-spec.md`  
**Focus:**
- Pages: Overview, Strategies, Positions, Runs/Backtests, Controls, System Health
- Charts: Equity curve, PnL, risk metrics
- Actions: Enable/disable strategies, adjust risk caps
- Data dependencies and API integration

## Deliverables Checklist

### `/plans` Folder
- [x] `task_plan.md` (this file)
- [x] `findings.md`
- [x] `progress.md`
- [x] `milestones.md`

### `/docs` Folder
- [x] `architecture.md`
- [x] `api-contracts.md`
- [x] `data-contracts.md`
- [x] `risk-policy.md`
- [x] `security.md`
- [x] `dashboard-spec.md`

### `/adr` Folder
- [x] ADRs as needed for key decisions

## Phase Gates

### Phase 1: Planning Initialization ✅
- [x] Read floorplan.md and research.md
- [x] Create folder structure
- [x] Initialize planning files

### Phase 2: Parallel Agent Documentation ✅
- [x] Launch all 5 specialist agents simultaneously
- [x] Each agent reads floorplan.md
- [x] Each agent produces assigned documentation

### Phase 3: Review & Integration ✅
- [x] Review all agent outputs for consistency
- [x] Resolve conflicts via ADRs
- [x] Ensure contracts are implementation-ready

### Phase 4: Cursor Handoff
- [x] Create Cursor Implementation Sprint section
- [x] Verify all docs exist and are consistent
- [x] Document risk gates and security controls

## Cursor Implementation Sprint (Handoff Plan)

This section guides the Cursor Agents for the build phase.

### Sprint 1: Infrastructure & Data (Days 1-3)
1. **Repo Setup:**
   - [x] Initialize git, poetry (Python), and npm (Node).
   - [x] Setup `docker-compose.yml` with Postgres (TimescaleDB) and Redis.
   - [x] Define shared Pydantic models in `packages/common/schemas.py` from `docs/data-contracts.md`.

2. **Data Service:**
   - [x] Implement `services/data` skeleton.
   - [x] Build `AlpacaProvider` class for historical/live data.
   - [x] Create Postgres tables using Alembic migrations.
   - [x] **Verification:** Fetch 1 year of AAPL data and verify in DB.

### Sprint 2: Feature Pipeline & Strategy Core (Days 4-6)
1. **Feature Engine:**
   - [x] Implement `services/features`.
   - [x] Create SMA, RSI, MACD calculators (manual implementation for Python 3.11 compatibility).
   - [ ] **Verification:** Compare computed properties against known-good values.

2. **Strategy Core:**
   - [x] Implement `packages/strategies/base.py` (Abstract Base Class).
   - [x] Create "Starter Strategy" (Simple Moving Average Crossover).
   - [ ] **Verification:** Run strategy on static dataset, log signals.

### Sprint 3: Backtesting & Reporting (Days 7-9) ✅ COMPLETE
1. **Backtest Service:**
   - [x] Implement `services/backtest` using Backtrader or vectorbt. (Custom lightweight engine chosen - see ADR-0005)
   - [x] Connect `Strategy` output to Backtest engine.
   - [x] Generate HTML report.
   - [x] **Verification:** Backtest Starter Strategy, ensure P&L math is correct.

### Sprint 4: Dashboard & API (Days 10-12) ✅ COMPLETE
1. **API Backend:**
   - [x] Implement FastAPI endpoints from `docs/api-contracts.md`.
   - [x] Wire up endpoints to Database (Read-only initially). *Note: Using mock data*
   
2. **Dashboard UI:**
   - [x] Scout Next.js app with `docs/dashboard-spec.md`.
   - [x] Build Overview Page and Strategy List.
   - [x] **Verification:** View Backtest results in Dashboard.

### Sprint 5: Execution & Risk (Days 13-14) ✅ COMPLETE
1. **Execution Engine:**
   - [x] Implement `services/execution` with OMS.
   - [x] Connect `BrokerClient` to Alpaca Paper API.
   - [x] Order lifecycle management (submit, fill, cancel).
   - [x] Position reconciliation with broker.
   
2. **Risk Guardrails:**
   - [x] Implement `services/risk` limits from `docs/risk-policy.md`.
   - [x] Kill switch (global and per-strategy).
   - [x] Circuit breaker for consecutive losses.
   - [x] Position size limits, drawdown controls.
   - [x] Middleware to block orders if risk check fails.
   - [x] **Verification:** Attempt to place order > 5% risk, verify rejection.

### Sprint 6: ML Safety & Interpretability Core (Days 15-18) ✅ COMPLETE
*Goal: Enable explicit model behavior under uncertainty, build trust through interpretability.*

1. **Model Drift & Decay Detection:**
   - [x] Feature distribution drift tracking (mean, std, PSI, KL divergence).
   - [x] Prediction confidence drift monitoring.
   - [x] Error drift tracking when ground truth becomes available.
   - [x] Threshold-based alerts for drift.
   - [x] Model "health score" derived from drift signals.
   - [x] Store and query drift metrics over time.
   - [x] **Verification:** Drift metrics queryable per model, per feature.

2. **Confidence Gating & Abstention Logic:**
   - [x] Extend model output schema: BUY / SELL / ABSTAIN.
   - [x] Configurable confidence thresholds per strategy.
   - [x] Entropy / uncertainty measure calculation.
   - [x] Ensemble disagreement signals.
   - [x] Update backtest engine to account for abstentions.
   - [x] **Verification:** Strategy abstains when confidence < threshold.

3. **Local Explainability (SHAP):**
   - [x] SHAP integration for tree-based models.
   - [x] Permutation importance as fallback.
   - [x] Explanation payload: features, influence direction (+/-), confidence.
   - [x] Store explanations alongside trade records.
   - [x] Dashboard UI to view trade explanations.
   - [x] **Verification:** Each recommendation has human-readable explanation.

4. **Human-in-the-Loop Controls:**
   - [x] Approval flag in execution pipeline.
   - [x] Recommendation queue (pending human approval).
   - [x] Manual override UI in dashboard.
   - [x] Log human vs model decisions for comparison.
   - [x] **Verification:** Trade requires explicit approval when HITL enabled.

5. **Regret & Baseline Comparison Metrics:**
   - [x] Baseline strategy implementations (hold cash, buy & hold, random-controlled).
   - [x] Regret metrics calculation vs baselines.
   - [x] Track regret over time.
   - [x] Dashboard visualization of relative performance.
   - [x] **Verification:** Dashboard shows "vs baseline" comparison.

6. **Polish & UX (from backlog):**
   - [x] Educational tooltips for trading terminology.
   - [x] Help page with glossary (P&L, Sharpe, Max Drawdown, Win Rate, etc.).
   - [x] Tooltip component for StatsCard and table headers.
   - [x] Vercel deployment configuration.
   - [x] **Verification:** Non-technical user can understand all metrics.

### Skills to Use for the upcoming Sprints
### ML & experimentation

1. **ml-pipeline-builder**
2. **feature-engineering**
3. **time-series-ml**
4. **ensemble-modeling**
5. **model-evaluation**
6. **experiment-tracking**

---

### Safety, correctness, robustness

7. **data-leakage-detector**
8. **risk-control-logic**
9. **abstention-logic**
10. **anomaly-detection**

---

### Backend & infra

11. **backend-service-architect**
12. **async-systems**
13. **database-schema-designer**
14. **caching-strategy**
15. **config-management**

---

### Observability & UX

16. **model-observability**
17. **explainability-ui**
18. **dashboard-architect**

---

### Dev velocity & quality

19. **refactor-engine**
20. **documentation-generator**


### Sprint 7: First ML Model (End-to-End Loop) (Days 19–22)
Goal: Introduce exactly one real ML model into the system and run it end-to-end with correct training, validation, inference, and execution semantics.

This sprint is about correctness, clarity, and learning — not performance or UI polish.

1. **ML Problem Definition**
   - Define target variable (e.g. probability of positive return over next N bars).
   - Define prediction horizon.
   - Define label construction logic.
   - Define evaluation metrics (classification or regression).
   - Document assumptions and failure modes.
   - Verification: Model target and metrics clearly documented.

2. **Training & Validation Pipeline**
   - Implement offline training script.
   - Time-aware train/validation split (walk-forward or sliding window).
   - Prevent data leakage explicitly.
   - Log training and validation metrics.
   - Verification: Training run reproducible and metrics logged.

3. **Model Interface & Contract**
   - Standardized model input schema.
   - Standardized output schema:
     - prediction
     - confidence
     - abstain signal
   - Explicit confidence semantics.
   - Verification: Execution layer can consume model output unambiguously.

4. **Inference Integration**
   - Run model inference in the live/paper pipeline.
   - Integrate with existing risk and execution layers.
   - Log predictions, confidence, and decisions.
   - Verification: Model predictions flow through full system.

5. **Text-Based Explainability (Initial)**
   - Simple explanation payload (features used, confidence, rationale).
   - Stored alongside predictions.
   - No SHAP yet.
   - Verification: Each prediction has a human-readable explanation.

Sprint 7 Success Criteria:
- Exactly one ML model runs end-to-end.
- Model behavior is understandable and inspectable.
- No silent failures or hidden assumptions.

**Actionable implementation:**

1. **ML Problem Definition:**
   - [ ] Define target variable (e.g. probability of positive return over next N bars).
   - [ ] Define prediction horizon and label construction logic.
   - [ ] Define evaluation metrics (classification or regression).
   - [ ] Document assumptions and failure modes.
   - [ ] **Verification:** Model target and metrics clearly documented.

2. **Training & Validation Pipeline:**
   - [ ] Implement offline training script.
   - [ ] Time-aware train/validation split (walk-forward or sliding window).
   - [ ] Explicit data leakage prevention (e.g. no future data in features).
   - [ ] Log training and validation metrics.
   - [ ] **Verification:** Training run reproducible and metrics logged.

3. **Model Interface & Contract:**
   - [ ] Standardized model input schema (features, symbol, timestamp).
   - [ ] Standardized output schema: prediction, confidence, abstain signal.
   - [ ] Explicit confidence semantics (e.g. 0–1, when to ABSTAIN).
   - [ ] **Verification:** Execution layer can consume model output unambiguously.

4. **Inference Integration:**
   - [ ] Run model inference in the live/paper pipeline (strategy or dedicated service).
   - [ ] Integrate model output with existing risk and execution layers.
   - [ ] Log predictions, confidence, and decisions (e.g. to DB or structured logs).
   - [ ] **Verification:** Model predictions flow through full system (data → model → signal → risk → order).

5. **Text-Based Explainability (Initial):**
   - [ ] Simple explanation payload (features used, confidence, short rationale).
   - [ ] Store explanations alongside predictions/trades.
   - [ ] **Verification:** Each prediction has a human-readable explanation (no SHAP required yet).


### Sprint 8: ML Observability, Safety & Evaluation (Days 23–26)
Goal: Make the first ML model observable, debuggable, and safe before scaling to multiple models.

1. **Model Performance Tracking**
   - Prediction vs outcome logging.
   - Rolling accuracy / error metrics.
   - Abstention rate tracking.
   - Verification: Performance queryable over time.

2. **Baseline & Regret Metrics**
   - Implement simple baselines (do nothing, buy & hold, random).
   - Compute regret relative to baselines.
   - Verification: Model performance contextualized.

3. **Confidence & Drift Monitoring**
   - Feature distribution drift.
   - Confidence drift.
   - Error drift once ground truth is available.
   - Health score derived from drift signals.
   - Verification: Drift metrics stored and queryable.

4. **Explainability (Advanced)**
   - SHAP for supported models.
   - Permutation importance fallback.
   - Store explanations per prediction.
   - Verification: Explanation available for each recommendation.

5. **Failure Mode & Stress Simulation**
   - Missing data simulation.
   - Volatility spike simulation.
   - API outage simulation.
   - Document system behavior under stress.
   - Verification: Failure modes are understood and documented.

Sprint 8 Success Criteria:
- Model failures are visible, not silent.
- Performance is contextualized, not absolute.
- System behavior under stress is understood.

**Actionable implementation:**

1. **Model Performance Tracking:**
   - [ ] Log prediction vs outcome (direction or return) when ground truth is available.
   - [ ] Compute rolling accuracy / error metrics (e.g. over last N days).
   - [ ] Track abstention rate over time.
   - [ ] Expose performance metrics via API or DB for dashboard.
   - [ ] **Verification:** Performance queryable per model over time.

2. **Baseline & Regret Metrics:**
   - [ ] Wire existing baselines (hold cash, buy & hold, random) to model strategy comparison.
   - [ ] Compute regret (strategy vs baselines) for the live model.
   - [ ] Store and expose regret metrics (e.g. API or dashboard feed).
   - [ ] **Verification:** Model performance contextualized vs baselines.

3. **Confidence & Drift Monitoring:**
   - [ ] Feed current feature (and confidence) distributions into existing drift detector.
   - [ ] Store reference (training) distributions for comparison.
   - [ ] Compute and store health score from drift signals.
   - [ ] Expose drift metrics and health via API (e.g. per model, per feature).
   - [ ] **Verification:** Drift metrics stored and queryable per model.

4. **Explainability (Advanced):**
   - [ ] Integrate SHAP (or permutation importance) for the deployed model’s predictions.
   - [ ] Store explanation payload per prediction/recommendation.
   - [ ] **Verification:** Explanation available for each recommendation (e.g. via API or trade record).

5. **Failure Mode & Stress Simulation:**
   - [ ] Implement or script: missing data simulation (e.g. drop bars, NaN features).
   - [ ] Implement or script: volatility spike simulation (e.g. scaled returns).
   - [ ] Implement or script: API outage simulation (e.g. broker unavailable).
   - [ ] Document system behavior under each scenario (no trade, abstain, fallback, etc.).
   - [ ] **Verification:** Failure modes are understood and documented (runbook or ADR).

### Sprint 9: Model Observatory Dashboard (Days 27–31)
*Goal: Make models inspectable, configurable, and comparable as first-class entities in the dashboard.*

1. **Model Registry UI:**
   - [ ] Dedicated Model Registry page in dashboard.
   - [ ] List view with sorting/filtering.
   - [ ] Display: name, type, status, trained date, health score, allocation weight.
   - [ ] Quick actions (activate, pause, view details).
   - [ ] **Verification:** All models visible in dashboard list.

2. **Model Detail Page:**
   - [ ] Model overview section (architecture, feature set, hyperparams).
   - [ ] Training & validation summary (period, method, metrics, overfitting indicators).
   - [ ] Live/paper performance (accuracy over time, abstention rate).
   - [ ] Confidence calibration plots.
   - [ ] **Verification:** Full model context visible on single page.

3. **ML Performance Visualization:**
   - [ ] Prediction vs actual plots (directional or regression).
   - [ ] Rolling accuracy charts.
   - [ ] Confusion matrix (for classification).
   - [ ] Calibration curves (confidence vs correctness).
   - [ ] Error distribution plots.
   - [ ] Toggle between ML metrics and trading metrics.
   - [ ] **Verification:** ML-native visualizations render correctly.

4. **Model Comparison & Ranking View:**
   - [ ] Side-by-side model comparison page.
   - [ ] Comparison dimensions: validation metrics, recent performance, drawdown, volatility.
   - [ ] Sorting/filtering (best performers, most stable, least risky).
   - [ ] Confidence stability and drift score comparison.
   - [ ] **Verification:** Can rank models by multiple criteria.

5. **Hyperparameter & Threshold Tuning Interface:**
   - [ ] Dashboard controls for confidence thresholds.
   - [ ] Abstention threshold adjustment.
   - [ ] Ensemble contribution caps.
   - [ ] Allocation limit controls.
   - [ ] Change confirmation modal with impact preview.
   - [ ] Change logging and rollback support.
   - [ ] **Verification:** Parameter changes reflected in model behavior.

6. **Model Lifecycle Controls:**
   - [ ] Activate / deactivate model from dashboard.
   - [ ] Promote candidate → active workflow.
   - [ ] Retire model action.
   - [ ] Freeze parameters toggle.
   - [ ] Clone model config for new experiment.
   - [ ] **Verification:** Lifecycle actions update model state correctly.

7. **Model Drift & Health Visualization UI:**
   - [ ] Per-model drift trend charts.
   - [ ] Feature drift heatmaps.
   - [ ] Health score timeline.
   - [ ] Alert badges and threshold indicators.
   - [ ] Suggested actions (retrain, retire).
   - [ ] **Verification:** Drift aging is visible, not silent.

8. **Human-in-the-Loop Review Mode (Model-Centric):**
   - [ ] Model recommendation review queue.
   - [ ] Explanation display per recommendation.
   - [ ] Approve/reject at model level.
   - [ ] Rationale input (optional).
   - [ ] Decision outcome logging.
   - [ ] **Verification:** User can review and decide on model recommendations.

9. **Model Sandbox / What-If Testing:**
   - [ ] Parameter modification sandbox (no live impact).
   - [ ] Rerun backtests with modified thresholds.
   - [ ] Temporarily disable models in sandbox.
   - [ ] Compare hypothetical allocations.
   - [ ] Preview effects before applying changes.
   - [ ] **Verification:** Safe experimentation without affecting live behavior.

## Sprint Summary

| Sprint | Focus | Days | Status |
|--------|-------|------|--------|
| 1 | Infrastructure & Data | 1-3 | ✅ Complete |
| 2 | Feature Pipeline & Strategy Core | 4-6 | ✅ Complete |
| 3 | Backtesting & Reporting | 7-9 | ✅ Complete |
| 4 | Dashboard & API | 10-12 | ✅ Complete |
| 5 | Execution & Risk | 13-14 | ✅ Complete |
| 6 | ML Safety & Interpretability | 15-18 | ✅ Complete |
| 7 | First ML Model (End-to-End Loop) | 19-22 | Not Started |
| 8 | ML Observability, Safety & Evaluation | 23-26 | Not Started |
| 9 | Model Observatory Dashboard | 27-31 | Not Started |

## Success Criteria
- ✅ All `/docs` files exist and are internally consistent
- ✅ Contracts are explicit enough for Cursor Agents to implement without guessing
- ✅ Risk and security gates are clearly defined
- ✅ `task_plan.md` includes a Cursor Implementation Sprint section

### Sprint 6 Success Criteria
- [ ] Model behavior under uncertainty is explicit (abstention, drift detection)
- [ ] Trade recommendations are interpretable (SHAP explanations)
- [ ] Human-in-the-loop approval works for cautious deployment
- [ ] Performance compared to baselines (regret metrics)

### Sprint 7 Success Criteria (First ML Model)
- [ ] Exactly one ML model runs end-to-end
- [ ] Model behavior is understandable and inspectable
- [ ] No silent failures or hidden assumptions

### Sprint 8 Success Criteria (ML Observability & Safety)
- [ ] Model failures are visible, not silent
- [ ] Performance is contextualized, not absolute (vs baselines)
- [ ] System behavior under stress is understood and documented

### Sprint 9 Success Criteria (Model Observatory Dashboard)
- [ ] Models are first-class entities in the dashboard
- [ ] ML-native visualizations (confusion matrix, calibration curves) available
- [ ] Users can compare and rank models side-by-side
- [ ] Parameter tuning is safe with preview and rollback
- [ ] Model lifecycle (activate, pause, retire) manageable from UI
- [ ] Dashboard supports learning and experimentation, not just monitoring

## Notes
- This project targets **risk level 6-7** (moderate): controlled drawdowns, risk-adjusted returns
- **Paper trading first**, then live with strict safeguards
- Dashboard deploys to **Vercel** (Next.js), trading services run separately
- Technology stack: Python 3.11+, FastAPI, pandas, scikit-learn/XGBoost, Next.js, Postgres
- Sprint 6 focus: **trustworthy ML platform** (safety, interpretability, baselines)
- Sprint 7 focus: **first ML model end-to-end** (training, inference, clarity)
- Sprint 8 focus: **observability and safety** (drift, stress testing, contextualized performance)
- Sprint 9 focus: **model-centric dashboard** for ML/SWE users with little trading experience
