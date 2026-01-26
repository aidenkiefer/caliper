# Sprint 4 Multi-Agent Workflow: Dashboard & API

**Sprint 4 Focus:** Build FastAPI backend endpoints and Next.js dashboard to view backtest results and monitor strategies

---

## 🎯 Sprint 4 Overview

**Goal:** Create a functional monitoring dashboard that displays backtest results, strategy performance, and system health through a REST API backend.

**Prerequisites:** Sprint 3 complete (backtesting engine, reports, P&L calculation)

**Parallelization:** ✅ High - Backend API and Frontend Dashboard can be developed in parallel

---

## 📋 Sprint 4 Tasks Breakdown

### Stream A: API Backend (Backend Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| A1 | Create FastAPI app structure | None |
| A2 | Implement `/v1/metrics/summary` endpoint | A1 |
| A3 | Implement `/v1/strategies` endpoints | A1 |
| A4 | Implement `/v1/runs` endpoints (backtest results) | A1 |
| A5 | Implement `/v1/positions` endpoints | A1 |
| A6 | Implement `/v1/health` endpoint | A1 |
| A7 | Wire endpoints to database queries | A2-A6 |

### Stream B: Dashboard UI (Frontend Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| B1 | Initialize Next.js 14 project | None |
| B2 | Setup Shadcn/UI + Tailwind | B1 |
| B3 | Create layout shell (sidebar, header) | B2 |
| B4 | Build Overview page (equity curve, stats) | B3 |
| B5 | Build Strategies list page | B3 |
| B6 | Build Runs/Backtests page | B3 |
| B7 | Build Run detail page (view report) | B3 |
| B8 | Setup API client (fetch from Backend) | B3, needs A7 |

### Stream C: Architecture Review (Architect Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| C1 | Review API implementation against contracts | A7 |
| C2 | Update `docs/architecture.md` with API layer | A7, B7 |
| C3 | Create ADR if significant decisions made | C1, C2 |

### Stream D: Testing (QA Agent) - SEQUENTIAL (after Backend)

| Task | Description | Dependencies |
|------|-------------|--------------|
| D1 | Write API integration tests | A7 |
| D2 | Create test fixtures for API | D1 |
| D3 | Write dashboard smoke tests | B7 |
| D4 | Create verification runbook | D1, D3 |

### Stream E: Infrastructure (DevOps Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| E1 | Update docker-compose for API service | None |
| E2 | Add API environment variables | E1 |
| E3 | Setup dashboard dev server config | B1 |

---

## 📊 Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SPRINT 4 PARALLEL EXECUTION                            │
└─────────────────────────────────────────────────────────────────────────────┘

                    START
                      │
    ┌─────────────────┼─────────────────┬─────────────────┐
    │                 │                 │                 │
    ▼                 ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐   ┌──────────┐    ┌────────────┐
│ Backend │    │  Frontend   │   │ DevOps   │    │ Architect  │
│ Agent   │    │   Agent     │   │  Agent   │    │   Agent    │
│ (A1-A7) │    │  (B1-B7)    │   │ (E1-E3)  │    │  (C1-C3)   │
└────┬────┘    └──────┬──────┘   └────┬─────┘    └──────┬─────┘
     │                │               │                 │
     │ A7 complete    │ B7 complete   │ E3 complete     │ Reviews
     │                │               │                 │ as work
     ▼                ▼               ▼                 │ completes
     └───────────────►├◄──────────────┘                 │
                      │                                 │
                      │ B8: Connect Frontend to API     │
                      │                                 │
                      ▼                                 │
               ┌─────────────┐                         │
               │  QA Agent   │◄────────────────────────┘
               │  (D1-D4)    │
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │ Integrator  │
               │ Final Pass  │
               └─────────────┘
```

**Parallelization Strategy:**
- **Backend Agent** and **Frontend Agent** start immediately (no dependencies)
- **DevOps Agent** starts immediately (infrastructure setup)
- **Architect Agent** starts immediately (can begin reviewing docs/contracts)
- **QA Agent** starts after Backend Agent completes testable endpoints
- **Frontend Agent Task B8** requires Backend Agent A7 to be complete

---

## 👥 Agent Assignment

### Backend Agent
**Owns:** Tasks A1-A7 (FastAPI Backend)

**Files:**
- `services/api/**/*.py`
- `services/api/README.md`
- `services/api/pyproject.toml`
- `packages/common/api_schemas.py` (response models)

**Cannot Touch:**
- `services/data/models.py` (Data Agent)
- `apps/dashboard/**` (Frontend Agent)
- `docker-compose.yml` (DevOps Agent)
- `tests/**` (QA Agent)

### Frontend Agent
**Owns:** Tasks B1-B8 (Next.js Dashboard)

**Files:**
- `apps/dashboard/**`
- `apps/dashboard/package.json`
- `apps/dashboard/README.md`

**Cannot Touch:**
- `services/**/*.py` (Backend Agent)
- `docker-compose.yml` (DevOps Agent)
- `tests/**` (QA Agent)

### Architect Agent
**Owns:** Tasks C1-C3 (Design Review)

**Files:**
- `docs/architecture.md` (updates)
- `docs/api-contracts.md` (validation/updates)
- `adr/*.md` (new ADRs if needed)

**Cannot Touch:**
- Any code files

### QA Agent
**Owns:** Tasks D1-D4 (Testing)

**Files:**
- `services/api/test_*.py`
- `tests/integration/test_api_*.py`
- `tests/fixtures/api_data.py`
- `docs/runbooks/api-verification.md`

**Cannot Touch:**
- Implementation files

### DevOps Agent
**Owns:** Tasks E1-E3 (Infrastructure)

**Files:**
- `docker-compose.yml` (updates)
- `configs/environments/.env.example` (updates)
- `apps/dashboard/.env.local.example`
- `scripts/**`

**Cannot Touch:**
- Application code

---

## 🛠️ Skills to Invoke Per Agent

### Backend Agent Skills

| Skill | Purpose | When |
|-------|---------|------|
| `@using-superpowers` | Skill protocol | ALWAYS FIRST |
| `@python-patterns` | FastAPI best practices | Before any Python code |
| `@api-patterns` | REST API design, response formats | Before implementing endpoints |
| `@clean-code` | Code quality, function size | During implementation |

**Skill Files:**
- `agents/skills/skills/using-superpowers/SKILL.md`
- `agents/skills/skills/python-patterns/SKILL.md`
- `agents/skills/skills/api-patterns/SKILL.md`
- `agents/skills/skills/clean-code/SKILL.md`

### Frontend Agent Skills

| Skill | Purpose | When |
|-------|---------|------|
| `@using-superpowers` | Skill protocol | ALWAYS FIRST |
| `@nextjs-best-practices` | Next.js App Router patterns | Before creating pages |
| `@react-patterns` | Component design, hooks | Before building components |
| `@tailwind-patterns` | Styling, responsive design | Before styling |
| `@clean-code` | Code quality | During implementation |

**Skill Files:**
- `agents/skills/skills/using-superpowers/SKILL.md`
- `agents/skills/skills/nextjs-best-practices/SKILL.md`
- `agents/skills/skills/react-patterns/SKILL.md`
- `agents/skills/skills/tailwind-patterns/SKILL.md`
- `agents/skills/skills/clean-code/SKILL.md`

### Architect Agent Skills

| Skill | Purpose | When |
|-------|---------|------|
| `@using-superpowers` | Skill protocol | ALWAYS FIRST |
| `@api-patterns` | Validate API design | During review |
| `@software-architecture` | System design review | During documentation |

**Skill Files:**
- `agents/skills/skills/using-superpowers/SKILL.md`
- `agents/skills/skills/api-patterns/SKILL.md`
- `agents/skills/skills/software-architecture/SKILL.md` (if available)

### QA Agent Skills

| Skill | Purpose | When |
|-------|---------|------|
| `@using-superpowers` | Skill protocol | ALWAYS FIRST |
| `@testing-patterns` | Test design, factories | Before writing tests |
| `@python-patterns` | Python test code | During test implementation |

**Skill Files:**
- `agents/skills/skills/using-superpowers/SKILL.md`
- `agents/skills/skills/testing-patterns/SKILL.md`
- `agents/skills/skills/python-patterns/SKILL.md`

### DevOps Agent Skills

| Skill | Purpose | When |
|-------|---------|------|
| `@using-superpowers` | Skill protocol | ALWAYS FIRST |
| `@docker-expert` | Docker best practices | When updating docker-compose |

**Skill Files:**
- `agents/skills/skills/using-superpowers/SKILL.md`
- `agents/skills/skills/docker-expert/SKILL.md` (if available)

---

## 📦 Sprint 4 Output Contracts

### Backend Agent Must Deliver:

1. **FastAPI Application (`services/api/`)**
   ```python
   # services/api/main.py
   app = FastAPI(title="Quant Platform API", version="1.0.0")
   
   # Routers
   app.include_router(metrics_router, prefix="/v1/metrics")
   app.include_router(strategies_router, prefix="/v1/strategies")
   app.include_router(runs_router, prefix="/v1/runs")
   app.include_router(positions_router, prefix="/v1/positions")
   app.include_router(health_router, prefix="/v1/health")
   ```

2. **Endpoints (per `docs/api-contracts.md`)**
   - `GET /v1/metrics/summary` - Aggregate metrics
   - `GET /v1/strategies` - List strategies
   - `GET /v1/strategies/{id}` - Strategy detail
   - `GET /v1/runs` - List backtest runs
   - `GET /v1/runs/{id}` - Run detail with results
   - `POST /v1/runs` - Trigger new backtest
   - `GET /v1/positions` - Current positions
   - `GET /v1/health` - System health

3. **Response Models (`packages/common/api_schemas.py`)**
   ```python
   class RunResponse(BaseModel):
       run_id: str
       strategy_id: str
       run_type: Literal["BACKTEST", "PAPER", "LIVE"]
       metrics: PerformanceMetrics
       equity_curve: List[EquityPoint]
       trades: List[Trade]
   ```

4. **Documentation**
   - `services/api/README.md` - Usage guide
   - Auto-generated OpenAPI at `/docs`

### Frontend Agent Must Deliver:

1. **Next.js 14 Application (`apps/dashboard/`)**
   - App Router structure
   - Shadcn/UI components installed
   - Tailwind CSS configured

2. **Pages**
   - `/` - Overview page (equity curve, summary stats)
   - `/strategies` - Strategy list with status
   - `/strategies/[id]` - Strategy detail
   - `/runs` - Backtest run history
   - `/runs/[id]` - Run detail with charts
   - `/health` - System health status

3. **Components**
   - Layout shell (sidebar navigation, header)
   - Equity curve chart (TradingView or Recharts)
   - Stats cards (P&L, Sharpe, drawdown)
   - Data tables (strategies, runs, positions)
   - Loading/error states

4. **API Integration**
   - API client utility
   - React Query or SWR for data fetching
   - Type-safe response handling

### Architect Agent Must Deliver:

1. **Documentation Updates**
   - `docs/architecture.md` updated with API service section
   - `docs/api-contracts.md` validated against implementation
   - Data flow diagram for API → Dashboard

2. **ADR (if needed)**
   - `adr/0006-api-architecture.md` (if significant decisions)

### QA Agent Must Deliver:

1. **API Tests**
   - `services/api/test_metrics.py`
   - `services/api/test_strategies.py`
   - `services/api/test_runs.py`
   - `tests/integration/test_api_e2e.py`

2. **Test Fixtures**
   - `tests/fixtures/api_data.py`

3. **Runbook**
   - `docs/runbooks/api-verification.md`

### DevOps Agent Must Deliver:

1. **Docker Updates**
   - API service in `docker-compose.yml`
   - Port mapping (8000)
   - Health check

2. **Environment Variables**
   - `API_HOST`, `API_PORT`
   - `CORS_ORIGINS`

---

## ✅ Sprint 4 Acceptance Criteria

### Functional Requirements

- [ ] **API Responds**
  - All endpoints return valid JSON
  - Response format matches `docs/api-contracts.md`
  - Error handling returns proper status codes

- [ ] **Dashboard Displays Data**
  - Overview page shows equity curve
  - Strategies page lists all strategies
  - Runs page shows backtest history
  - Run detail page displays full report

- [ ] **Integration Works**
  - Dashboard fetches data from API
  - Backtest results visible in dashboard
  - Health status displays correctly

### Technical Requirements

- [ ] **Code Quality**
  - Backend follows `@python-patterns` and `@api-patterns`
  - Frontend follows `@nextjs-best-practices` and `@react-patterns`
  - All code follows `@clean-code`

- [ ] **Tests Pass**
  - API tests: `poetry run pytest services/api/`
  - Integration test: API → Dashboard flow works

- [ ] **Performance**
  - API responds in < 500ms for list endpoints
  - Dashboard loads in < 3s

### Documentation Requirements

- [ ] **API Documented**
  - OpenAPI spec at `/docs`
  - `services/api/README.md` complete

- [ ] **Dashboard Documented**
  - `apps/dashboard/README.md` complete
  - Setup instructions provided

- [ ] **Architecture Updated**
  - `docs/architecture.md` includes API layer

---

## 🎬 Sprint 4 Agent Prompts

See `docs/SPRINT4_AGENT_PROMPTS.md` for copy-paste ready prompts for each agent.

---

## 🔄 Sprint 4 Integrator Prompt

**Run this in Composer 1 AFTER all agents complete:**

```
You are the Integrator for Sprint 4: Dashboard & API.

Read:
1. docs/sprint-4-multi.md (Sprint 4 requirements)
2. Backend Agent's output summary
3. Frontend Agent's output summary  
4. Architect Agent's output summary
5. QA Agent's output summary
6. DevOps Agent's output summary

Your Tasks:

1. Merge Agent Outputs
   - Verify file ownership boundaries respected
   - Ensure no conflicts
   - Check consistency

2. Verify Integration
   - Start API: cd services/api && poetry run uvicorn main:app --reload
   - Start Dashboard: cd apps/dashboard && npm run dev
   - Test: Dashboard should display data from API
   - Verify: Backtest results visible in dashboard

3. Run Acceptance Tests
   - API tests: poetry run pytest services/api/
   - Integration test: Full API → Dashboard flow

4. Verify Sprint 4 Completion
   - Check all acceptance criteria from docs/sprint-4-multi.md
   - Verify documentation updated
   - Verify tests pass

5. Update Progress
   - Mark Sprint 4 tasks complete in plans/task_plan.md
   - Update plans/progress.md
   - Create SPRINT4_SUMMARY.md

Output Format:
1. Merge summary
2. Integration test results
3. Acceptance criteria status
4. Documentation updates
5. Sprint 4 completion confirmation
```

---

## 🚨 Sprint 4 Red Flags

**STOP if you see:**

- Backend Agent editing `apps/dashboard/**` → Frontend Agent owns that
- Frontend Agent editing `services/**/*.py` → Backend Agent owns that
- QA Agent editing implementation files → They only write tests
- Architect Agent writing code → They only do docs
- Skills not invoked → Mandatory before coding
- API responses not matching `docs/api-contracts.md` → Must follow contracts

---

## 📚 Sprint 4 Reference Files

**Must Read:**
- `docs/sprint-4-multi.md` (this file)
- `docs/WORKFLOW.md` (multi-agent protocol)
- `docs/api-contracts.md` (API specification)
- `docs/dashboard-spec.md` (Dashboard specification)
- `docs/architecture.md` (system design)

**Reference:**
- `services/backtest/` (Sprint 3 outputs to display)
- `packages/common/schemas.py` (data models)
- Agent briefs: `agents/briefs/*.md`

**Skills:**
- `agents/skills/skills/using-superpowers/SKILL.md`
- `agents/skills/skills/python-patterns/SKILL.md`
- `agents/skills/skills/api-patterns/SKILL.md`
- `agents/skills/skills/nextjs-best-practices/SKILL.md`
- `agents/skills/skills/react-patterns/SKILL.md`
- `agents/skills/skills/tailwind-patterns/SKILL.md`
- `agents/skills/skills/testing-patterns/SKILL.md`
- `agents/skills/skills/clean-code/SKILL.md`

---

## ✅ Sprint 4 Success Criteria

**Sprint 4 is complete when:**

- [ ] FastAPI endpoints respond correctly (match api-contracts.md)
- [ ] Dashboard displays overview, strategies, runs pages
- [ ] Backtest results visible in dashboard
- [ ] All tests pass
- [ ] Documentation updated
- [ ] `plans/task_plan.md` marked complete

---

## 🎯 Next Steps After Sprint 4

**Sprint 5:** Execution & Risk
- Execution engine (`services/execution`)
- Risk guardrails (`services/risk`)
- Paper trading integration
- Kill switch implementation

**Preparation:**
- Dashboard will display real-time positions
- API will expose execution and risk endpoints
- QA will test risk limit enforcement

---

**Last Updated:** 2026-01-26  
**Sprint Status:** ✅ COMPLETE  
**Completion Date:** 2026-01-26

---

## Post-Sprint Architecture Review

After all agents complete, the Architect Agent should:
1. Review all new code in services/api/ and apps/dashboard/
2. Ensure docs/architecture.md reflects the actual implementation
3. Update any diagrams or data flows
4. Document any architectural decisions made during implementation
5. Create ADR if significant decisions were made

### Architecture Review Checklist

- [ ] `services/api/` follows router-based modular structure
- [ ] `apps/dashboard/` follows Next.js App Router patterns
- [ ] Data flow: Dashboard → API → (Mock Data / Future: Database)
- [ ] Response models in `packages/common/api_schemas.py` match API contracts
- [ ] Error handling consistent across all endpoints
- [ ] Loading and error states implemented in dashboard
- [ ] ADR-0006 documents key decisions (mock data approach, router structure)
