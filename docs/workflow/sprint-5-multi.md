# Sprint 5 Multi-Agent Workflow: Execution & Risk

**Sprint 5 Focus:** Implement execution engine with Alpaca Paper API integration and comprehensive risk management with kill switches

---

## 🎯 Sprint 5 Overview

**Goal:** Build a complete execution and risk management layer that enables paper trading with strict risk controls, position tracking, and automated kill switches.

**Prerequisites:** Sprint 4 complete (API backend, dashboard)

**Parallelization:** ✅ Medium - Execution and Risk services can develop in parallel, but API integration depends on both

---

## 📋 Sprint 5 Tasks Breakdown

### Stream A: Execution Engine (Backend Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| A1 | Create `services/execution` skeleton with project structure | None |
| A2 | Implement `BrokerClient` abstract interface | A1 |
| A3 | Implement `AlpacaClient` (Paper trading mode) | A2 |
| A4 | Implement Order Management System (OMS) with state machine | A2 |
| A5 | Implement position tracking and reconciliation | A3, A4 |
| A6 | Implement order idempotency (unique client_order_id) | A4 |

### Stream B: Risk Management (Backend Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| B1 | Create `services/risk` skeleton with project structure | None |
| B2 | Implement `RiskManager` class with pre-trade checks | B1 |
| B3 | Implement portfolio-level limits (max drawdown, capital deployed) | B2 |
| B4 | Implement strategy-level limits (allocation, daily loss) | B2 |
| B5 | Implement order-level limits (position sizing, sanity checks) | B2 |
| B6 | Implement kill switch mechanism (system and strategy-level) | B3, B4 |
| B7 | Implement circuit breaker with automatic triggers | B6 |

### Stream C: API Integration (Backend Agent) - SEQUENTIAL (after A & B)

| Task | Description | Dependencies |
|------|-------------|--------------|
| C1 | Add `/v1/controls/kill-switch` endpoint | B6 |
| C2 | Add `/v1/controls/mode-transition` endpoint | A3, B6 |
| C3 | Update `/v1/health` with broker connection status | A3 |
| C4 | Add `/v1/orders` endpoint for order submission | A4, B2 |
| C5 | Add `/v1/orders/{id}` for order status tracking | A4 |

### Stream D: Architecture Review (Architect Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| D1 | Review execution service against `docs/architecture.md` | A5 |
| D2 | Review risk service against `docs/risk-policy.md` | B7 |
| D3 | Update `docs/architecture.md` with execution/risk details | D1, D2 |
| D4 | Create ADR-0007 for execution architecture decisions | D3 |

### Stream E: Testing (QA Agent) - SEQUENTIAL (after Backend)

| Task | Description | Dependencies |
|------|-------------|--------------|
| E1 | Write unit tests for `RiskManager` (all limit types) | B5 |
| E2 | Write integration tests for order rejection scenarios | B7, C4 |
| E3 | Write mock broker client tests (no live API calls) | A3 |
| E4 | Write kill switch activation tests | B6, C1 |
| E5 | Create verification runbook for execution/risk | E1-E4 |

### Stream F: Infrastructure (DevOps Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| F1 | Add Alpaca API credentials to `.env.example` | None |
| F2 | Update `docker-compose.yml` for execution/risk services | None |
| F3 | Configure paper/live mode environment separation | F1 |
| F4 | Add MODE validation on startup (paper vs live safety) | F3 |

### Stream G: Integration & Documentation (Integrator Agent) - FINAL

| Task | Description | Dependencies |
|------|-------------|--------------|
| G1 | Verify all agent deliverables are complete | A-F complete |
| G2 | Run all tests and verify acceptance criteria | G1 |
| G3 | Write `plans/SPRINT5_SUMMARY.md` with tasks, files, skills per agent | G2 |
| G4 | Update `plans/task_plan.md` - mark Sprint 5 complete | G3 |
| G5 | Update `plans/progress.md` - update current phase and status | G3 |
| G6 | Update `plans/milestones.md` - mark Sprint 5 deliverables complete | G3 |
| G7 | Update `README.md` - reflect Sprint 5 completion | G3 |
| G8 | Update `docs/FEATURES.md` - add execution/risk features | G3 |
| G9 | Final verification that all docs reflect current project state | G4-G8 |

---

## 📊 Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SPRINT 5 EXECUTION PLAN                                │
└─────────────────────────────────────────────────────────────────────────────┘

                    START
                      │
    ┌─────────────────┼─────────────────┬─────────────────┐
    │                 │                 │                 │
    ▼                 ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐   ┌──────────┐    ┌────────────┐
│ Backend │    │  Backend    │   │ DevOps   │    │ Architect  │
│ Agent   │    │   Agent     │   │  Agent   │    │   Agent    │
│ Stream A│    │  Stream B   │   │ (F1-F4)  │    │  (D1-D4)   │
│(Exec)   │    │  (Risk)     │   └────┬─────┘    └──────┬─────┘
└────┬────┘    └──────┬──────┘        │                 │
     │                │               │ F4 complete     │ Reviews
     │ A5 complete    │ B7 complete   │                 │ as work
     │                │               │                 │ completes
     └───────────────►├◄──────────────┘                 │
                      │                                 │
                      │ Backend Stream C (API)          │
                      │ (C1-C5)                         │
                      │                                 │
                      ▼                                 │
               ┌─────────────┐                         │
               │  QA Agent   │◄────────────────────────┘
               │  (E1-E5)    │
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │ Integrator  │
               │  (G1-G2)    │
               │ Verification│
               └──────┬──────┘
                      │
                      ▼
               ┌─────────────┐
               │ Integrator  │
               │  (G3-G9)    │
               │Sprint Summary│
               │  & Doc      │
               │  Updates    │
               └─────────────┘
```

**Parallelization Strategy:**
- **Backend Agent Stream A** (Execution) and **Stream B** (Risk) start immediately in parallel
- **DevOps Agent** starts immediately (infrastructure setup)
- **Architect Agent** starts immediately (can begin reviewing docs/contracts)
- **Backend Agent Stream C** starts after A and B complete
- **QA Agent** starts after Backend completes testable services
- **Integrator** runs final verification (G1-G2)
- **Integrator** writes sprint summary and updates all documentation (G3-G9)

---

## 👥 Agent Assignment

### Backend Agent
**Owns:** Tasks A1-A6, B1-B7, C1-C5 (Execution & Risk Services)

**Files:**
- `services/execution/**/*.py`
- `services/execution/README.md`
- `services/execution/pyproject.toml`
- `services/risk/**/*.py`
- `services/risk/README.md`
- `services/risk/pyproject.toml`
- `services/api/routers/orders.py` (new)
- `services/api/routers/controls.py` (new)
- `packages/common/execution_schemas.py` (new)

**Cannot Touch:**
- `apps/dashboard/**` (Frontend Agent)
- `docker-compose.yml` (DevOps Agent)
- `tests/**` (QA Agent)
- `docs/architecture.md` (Architect Agent)

### Architect Agent
**Owns:** Tasks D1-D4 (Design Review)

**Files:**
- `docs/architecture.md` (update execution/risk sections)
- `adr/0007-execution-architecture.md` (new)

**Cannot Touch:**
- `services/**/*.py` (Backend Agent)
- `docker-compose.yml` (DevOps Agent)
- `tests/**` (QA Agent)

### QA Agent
**Owns:** Tasks E1-E5 (Testing)

**Files:**
- `tests/unit/test_risk_manager.py`
- `tests/unit/test_execution.py`
- `tests/integration/test_order_flow.py`
- `tests/integration/test_kill_switch.py`
- `tests/fixtures/execution_data.py`
- `docs/runbooks/execution-verification.md`

**Cannot Touch:**
- `services/**/*.py` (Backend Agent)
- `apps/dashboard/**` (Frontend Agent)
- `docker-compose.yml` (DevOps Agent)

### DevOps Agent
**Owns:** Tasks F1-F4 (Infrastructure)

**Files:**
- `docker-compose.yml`
- `configs/environments/.env.example`
- `Dockerfile.execution` (if needed)
- `Makefile` (add execution targets)

**Cannot Touch:**
- `services/**/*.py` (Backend Agent)
- `apps/dashboard/**` (Frontend Agent)
- `tests/**` (QA Agent)

---

## 🛠️ Required Skills per Agent

### Backend Agent
| Skill | Purpose | Checklist |
|-------|---------|-----------|
| `@using-superpowers` | Skill invocation protocol | ☐ Read before ANY work |
| `@python-patterns` | FastAPI, async, Pydantic, type hints | ☐ Broker adapter pattern |
| `@api-patterns` | REST design, error handling | ☐ Controls endpoints |
| `@clean-code` | Code quality standards | ☐ Small functions, clear naming |

### Architect Agent
| Skill | Purpose | Checklist |
|-------|---------|-----------|
| `@using-superpowers` | Skill invocation protocol | ☐ Read before ANY work |
| `@api-patterns` | Validate API design | ☐ Review endpoints |
| `@software-architecture` | System design review | ☐ Execution flow diagrams |

### QA Agent
| Skill | Purpose | Checklist |
|-------|---------|-----------|
| `@using-superpowers` | Skill invocation protocol | ☐ Read before ANY work |
| `@testing-patterns` | TDD, mocking, test structure | ☐ Factory pattern for test data |
| `@python-patterns` | pytest, fixtures | ☐ Async test patterns |

### DevOps Agent
| Skill | Purpose | Checklist |
|-------|---------|-----------|
| `@using-superpowers` | Skill invocation protocol | ☐ Read before ANY work |
| `@docker-expert` | Container configuration | ☐ Service isolation |

---

## 📄 Output Contracts

### Backend Agent Deliverables

1. **Execution Service** (`services/execution/`)
   - `__init__.py`, `main.py`
   - `broker/__init__.py`, `broker/base.py`, `broker/alpaca.py`
   - `oms.py` (Order Management System)
   - `reconciliation.py` (Position reconciliation)
   - `README.md` with usage examples

2. **Risk Service** (`services/risk/`)
   - `__init__.py`, `main.py`
   - `manager.py` (RiskManager class)
   - `limits.py` (Portfolio, Strategy, Order limits)
   - `kill_switch.py` (Kill switch mechanism)
   - `circuit_breaker.py` (Automatic triggers)
   - `README.md` with configuration guide

3. **API Routes**
   - `services/api/routers/orders.py` - POST/GET orders
   - `services/api/routers/controls.py` - Kill switch, mode transition

4. **Schemas**
   - `packages/common/execution_schemas.py` - Order, Position, Fill models

### QA Agent Deliverables

1. **Unit Tests** (target: 50+ tests)
   - `tests/unit/test_risk_manager.py`
   - `tests/unit/test_execution.py`

2. **Integration Tests** (target: 15+ tests)
   - `tests/integration/test_order_flow.py`
   - `tests/integration/test_kill_switch.py`

3. **Verification Runbook**
   - `docs/runbooks/execution-verification.md`

### Architect Agent Deliverables

1. **Updated Architecture** (`docs/architecture.md`)
   - Execution service section with flow diagrams
   - Risk service section with limit descriptions
   - Order lifecycle state machine

2. **ADR** (`adr/0007-execution-architecture.md`)
   - Decision: Alpaca Paper API for v1
   - Decision: Single-service execution (not microservice per broker)
   - Decision: Synchronous order placement with async status polling

### DevOps Agent Deliverables

1. **Environment Variables**
   - `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`
   - `ALPACA_BASE_URL` (paper vs live)
   - `TRADING_MODE` (PAPER/LIVE)

2. **Docker Updates**
   - Service definitions for execution/risk
   - Health checks for broker connectivity

### Integrator Agent Deliverables

1. **Sprint Summary** (`plans/SPRINT5_SUMMARY.md`)
   - Tasks completed by each agent
   - Files created/modified per agent
   - Skills used by each agent with evidence
   - Known issues or limitations
   - Test results summary

2. **Documentation Updates**
   - `plans/task_plan.md` - Sprint 5 marked complete
   - `plans/progress.md` - Current phase updated
   - `plans/milestones.md` - Sprint 5 deliverables checked
   - `README.md` - Sprint 5 status and features
   - `docs/FEATURES.md` - Execution and risk features added

---

## ✅ Acceptance Criteria

### Execution Service
- [ ] `BrokerClient` interface with Alpaca implementation
- [ ] Paper trading orders can be placed via API
- [ ] Order status tracking (pending → filled/rejected)
- [ ] Position reconciliation matches broker state
- [ ] Unique `client_order_id` prevents duplicate orders

### Risk Service
- [ ] Pre-trade checks reject orders violating limits
- [ ] Portfolio limits: Max drawdown (10%), Max capital (80%)
- [ ] Strategy limits: Max allocation, daily loss limit
- [ ] Order limits: Max 2% risk per trade, $25k notional cap
- [ ] Kill switch halts all trading when triggered
- [ ] Circuit breaker auto-triggers on drawdown threshold

### API Integration
- [ ] `POST /v1/controls/kill-switch` activates/deactivates kill switch
- [ ] `POST /v1/orders` submits order through risk checks
- [ ] `GET /v1/health` shows broker connection status

### Testing
- [ ] All unit tests pass (50+ tests)
- [ ] Order rejection test: 5% risk order → rejected
- [ ] Kill switch test: Activates and blocks new orders
- [ ] Mock broker tests: No live API calls in tests

---

## 🔐 Risk Policy Implementation Reference

From `docs/risk-policy.md`:

### Portfolio-Level Limits
| Metric | Default Limit | Action |
|--------|---------------|--------|
| Max Daily Drawdown | 3% | Halt new entries |
| Max Total Drawdown | 10% | Kill switch |
| Max Capital Deployed | 80% | Reject orders |
| Max Open Positions | 20 | Reject orders |

### Order-Level Limits
| Metric | Limit | Action |
|--------|-------|--------|
| Max Risk Per Trade | 2% equity | Reject |
| Max Notional | $25,000 | Reject |
| Price Deviation | >5% from last | Reject |
| Min Stock Price | $5.00 | Reject |

### Kill Switch Protocol
1. Cancel all pending orders
2. Halt all strategy execution
3. Freeze positions (default) or flatten (configurable)
4. Send CRITICAL alert
5. Require manual admin reset

---

## 📋 Sprint Status

**Status:** 🟡 NOT STARTED  
**Target Duration:** Days 13-14  
**Agents Required:** 4 (Backend, Architect, QA, DevOps)

---

## 🚀 Quick Start

See `docs/workflow/SPRINT5_AGENT_PROMPTS.md` for copy-paste ready prompts for each agent.

**Execution Order:**
1. **Phase 1:** Backend (A+B), DevOps, Architect start in parallel
2. **Phase 2:** Backend Stream C (API integration)
3. **Phase 3:** QA Agent (testing)
4. **Phase 4:** Integrator verification (G1-G2)
5. **Phase 5:** Integrator writes sprint summary and updates all docs (G3-G9)

---

## 📚 Reference Documents

**Must Read:**
- `docs/risk-policy.md` - All risk limits and kill switch protocol
- `docs/security.md` - API key handling, mode separation
- `docs/api-contracts.md` - Controls and orders endpoints
- `docs/architecture.md` - Execution and risk service specs

**Agent Briefs:**
- `agents/briefs/BACKEND.md`
- `agents/briefs/ARCHITECT.md`
- `agents/briefs/QA.md`
- `agents/briefs/DEVOPS.md`

**Skills:**
- `agents/skills/skills/using-superpowers/SKILL.md` (MANDATORY)
- `agents/skills/skills/python-patterns/SKILL.md`
- `agents/skills/skills/api-patterns/SKILL.md`
- `agents/skills/skills/testing-patterns/SKILL.md`
- `agents/skills/skills/clean-code/SKILL.md`
- `agents/skills/skills/docker-expert/SKILL.md`
