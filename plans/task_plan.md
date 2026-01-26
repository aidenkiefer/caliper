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

### Sprint 5: Execution & Risk (Days 13-14)
1. **Execution Engine:**
   - [ ] Implement `services/execution`.
   - [ ] Connect `BrokerClient` to Alpaca Paper API.
   
2. **Risk Guardrails:**
   - [ ] Implement `services/risk` limits from `docs/risk-policy.md`.
   - [ ] Middleware to block orders if risk check fails.
   - [ ] **Verification:** Attempt to place order > 5% risk, verify rejection.

## Success Criteria
- ✅ All `/docs` files exist and are internally consistent
- ✅ Contracts are explicit enough for Cursor Agents to implement without guessing
- ✅ Risk and security gates are clearly defined
- ✅ `task_plan.md` includes a Cursor Implementation Sprint section

## Notes
- This project targets **risk level 6-7** (moderate): controlled drawdowns, risk-adjusted returns
- **Paper trading first**, then live with strict safeguards
- Dashboard deploys to **Vercel** (Next.js), trading services run separately
- Technology stack: Python 3.11+, FastAPI, pandas, scikit-learn/XGBoost, Next.js, Postgres
