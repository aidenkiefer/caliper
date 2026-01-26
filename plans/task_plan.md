# Quant ML Trading Platform - Task Plan

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

### Sprint 6: ML Safety & Interpretability Core (Days 15-18)
*Goal: Enable explicit model behavior under uncertainty, build trust through interpretability.*

1. **Model Drift & Decay Detection:**
   - [ ] Feature distribution drift tracking (mean, std, PSI, KL divergence).
   - [ ] Prediction confidence drift monitoring.
   - [ ] Error drift tracking when ground truth becomes available.
   - [ ] Threshold-based alerts for drift.
   - [ ] Model "health score" derived from drift signals.
   - [ ] Store and query drift metrics over time.
   - [ ] **Verification:** Drift metrics queryable per model, per feature.

2. **Confidence Gating & Abstention Logic:**
   - [ ] Extend model output schema: BUY / SELL / ABSTAIN.
   - [ ] Configurable confidence thresholds per strategy.
   - [ ] Entropy / uncertainty measure calculation.
   - [ ] Ensemble disagreement signals.
   - [ ] Update backtest engine to account for abstentions.
   - [ ] **Verification:** Strategy abstains when confidence < threshold.

3. **Local Explainability (SHAP):**
   - [ ] SHAP integration for tree-based models.
   - [ ] Permutation importance as fallback.
   - [ ] Explanation payload: features, influence direction (+/-), confidence.
   - [ ] Store explanations alongside trade records.
   - [ ] Dashboard UI to view trade explanations.
   - [ ] **Verification:** Each recommendation has human-readable explanation.

4. **Human-in-the-Loop Controls:**
   - [ ] Approval flag in execution pipeline.
   - [ ] Recommendation queue (pending human approval).
   - [ ] Manual override UI in dashboard.
   - [ ] Log human vs model decisions for comparison.
   - [ ] **Verification:** Trade requires explicit approval when HITL enabled.

5. **Regret & Baseline Comparison Metrics:**
   - [ ] Baseline strategy implementations (hold cash, buy & hold, random-controlled).
   - [ ] Regret metrics calculation vs baselines.
   - [ ] Track regret over time.
   - [ ] Dashboard visualization of relative performance.
   - [ ] **Verification:** Dashboard shows "vs baseline" comparison.

6. **Polish & UX (from backlog):**
   - [ ] Educational tooltips for trading terminology.
   - [ ] Help page with glossary (P&L, Sharpe, Max Drawdown, Win Rate, etc.).
   - [ ] Tooltip component for StatsCard and table headers.
   - [ ] Vercel deployment configuration.
   - [ ] **Verification:** Non-technical user can understand all metrics.

### Sprint 7: MLOps & Advanced Analysis (Days 19-22)
*Goal: Build operational infrastructure for reproducibility, simulation, and intelligent capital allocation.*

1. **Feature Registry & Lineage Tracking:**
   - [ ] Feature registry schema (name, definition, window/params, source, version).
   - [ ] Database table or metadata store implementation.
   - [ ] Feature versioning support.
   - [ ] Link features → models → experiments.
   - [ ] **Verification:** Feature used in model traceable to definition.

2. **Experiment Registry & Research Traceability:**
   - [ ] Experiment registry schema (dataset version, feature set, model type, hyperparams, metrics).
   - [ ] Deployment status tracking (research → staging → production).
   - [ ] Links between experiments, models, and live runs.
   - [ ] Queryable history of model evolution.
   - [ ] **Verification:** Can answer "why did we deploy this model?"

3. **Dynamic Capital Allocation:**
   - [ ] Capital allocation policy module.
   - [ ] Inputs: recent performance, drawdown, volatility, confidence/drift scores.
   - [ ] Per-model allocation caps.
   - [ ] Integration with ensemble layer.
   - [ ] Logged allocation decisions for auditability.
   - [ ] **Verification:** Capital shifts away from underperforming models.

4. **Failure Mode & Stress Simulation:**
   - [ ] Scenario simulation framework.
   - [ ] Volatility spike simulation.
   - [ ] Missing/delayed data simulation.
   - [ ] Poor fills / increased slippage simulation.
   - [ ] API outage simulation.
   - [ ] Partial execution failure simulation.
   - [ ] Stress-test reports.
   - [ ] Documented failure handling strategies.
   - [ ] **Verification:** System behavior documented under adverse conditions.

5. **Counterfactual & What-If Analysis:**
   - [ ] Parameterized backtest reruns.
   - [ ] Dashboard controls for what-if scenarios.
   - [ ] Scenarios: confidence threshold, model exclusion, trade delay.
   - [ ] Comparison metrics vs baseline run.
   - [ ] **Verification:** Can compare "what if" scenarios in dashboard.

## Sprint Summary

| Sprint | Focus | Days | Status |
|--------|-------|------|--------|
| 1 | Infrastructure & Data | 1-3 | ✅ Complete |
| 2 | Feature Pipeline & Strategy Core | 4-6 | ✅ Complete |
| 3 | Backtesting & Reporting | 7-9 | ✅ Complete |
| 4 | Dashboard & API | 10-12 | ✅ Complete |
| 5 | Execution & Risk | 13-14 | ✅ Complete |
| 6 | ML Safety & Interpretability | 15-18 | Not Started |
| 7 | MLOps & Advanced Analysis | 19-22 | Not Started |

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

### Sprint 7 Success Criteria
- [ ] Results are reproducible (feature registry, experiment tracking)
- [ ] System failure modes are understood (stress testing)
- [ ] Adding or removing models is safe (dynamic capital allocation)
- [ ] "What if" analysis enables safer tuning

## Notes
- This project targets **risk level 6-7** (moderate): controlled drawdowns, risk-adjusted returns
- **Paper trading first**, then live with strict safeguards
- Dashboard deploys to **Vercel** (Next.js), trading services run separately
- Technology stack: Python 3.11+, FastAPI, pandas, scikit-learn/XGBoost, Next.js, Postgres
- Sprint 6-7 focus: **trustworthy ML platform** over profit maximization
