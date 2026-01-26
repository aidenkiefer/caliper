# Sprint 4 Agent Prompts with Skill Gates

**Generated:** 2026-01-26  
**Sprint:** Dashboard & API  
**Status:** Ready for Execution

---

## 📋 Sprint 4 Task Coverage Verification

| Task | Agent | Status |
|------|-------|--------|
| FastAPI App Structure | Backend | ✅ Assigned |
| Metrics Endpoint | Backend | ✅ Assigned |
| Strategies Endpoints | Backend | ✅ Assigned |
| Runs Endpoints | Backend | ✅ Assigned |
| Positions Endpoints | Backend | ✅ Assigned |
| Health Endpoint | Backend | ✅ Assigned |
| Next.js Setup | Frontend | ✅ Assigned |
| Layout & Navigation | Frontend | ✅ Assigned |
| Overview Page | Frontend | ✅ Assigned |
| Strategies Page | Frontend | ✅ Assigned |
| Runs/Backtests Page | Frontend | ✅ Assigned |
| API Integration | Frontend | ✅ Assigned |
| API Tests | QA | ✅ Assigned |
| Design Review | Architect | ✅ Assigned |
| Docker Updates | DevOps | ✅ Assigned |

---

## 🎯 Sprint 4 Dependencies & Parallelization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SPRINT 4 PARALLEL EXECUTION PLAN                          │
└─────────────────────────────────────────────────────────────────────────────┘

START IMMEDIATELY (No Dependencies):
├── Backend Agent (Tasks A1-A7)
├── Frontend Agent (Tasks B1-B7)
├── DevOps Agent (Tasks E1-E3)
└── Architect Agent (Tasks C1-C3) - Reviews as work progresses

AFTER BACKEND COMPLETES:
├── QA Agent (Tasks D1-D4) - Needs testable endpoints
└── Frontend Agent Task B8 - Connect to API

FINAL:
└── Integrator - Merge and verify
```

**Execution Order:**
1. **Phase 1:** Backend, Frontend, DevOps, Architect start in parallel
2. **Phase 2:** QA Agent starts after Backend provides endpoints
3. **Phase 3:** Frontend connects to API (B8)
4. **Phase 4:** Integrator merges and verifies

---

## 👤 Backend Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the Backend Agent for Sprint 4: Dashboard & API.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY CODING
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills
You MUST invoke these skills before coding:

1. @python-patterns
   - Read: agents/skills/skills/python-patterns/SKILL.md
   - Purpose: FastAPI best practices, async patterns, type hints
   - Checklist:
     - [ ] Chosen FastAPI for API-first service
     - [ ] Using async def for I/O-bound operations
     - [ ] Type hints on all functions
     - [ ] Pydantic models for validation
     - [ ] Dependency injection pattern

2. @api-patterns
   - Read: agents/skills/skills/api-patterns/SKILL.md
   - Purpose: REST API design, response formats, error handling
   - Checklist:
     - [ ] RESTful resource naming (nouns, not verbs)
     - [ ] Consistent response envelope format
     - [ ] Proper HTTP status codes
     - [ ] Error response format defined
     - [ ] Pagination for list endpoints

3. @clean-code
   - Read: agents/skills/skills/clean-code/SKILL.md
   - Purpose: Code quality, function size, naming
   - Checklist:
     - [ ] Functions are small (max 20 lines)
     - [ ] Single responsibility per function
     - [ ] Clear naming (verb + noun for functions)
     - [ ] No magic numbers
     - [ ] Guard clauses for edge cases

STEP 3: Mark Skill Checklists Complete
Before coding, mark each checklist item as complete or explain why N/A.

IF SKILLS CANNOT BE INVOKED: STOP and explain why.

═══════════════════════════════════════════════════════════════
📚 CONTEXT READING
═══════════════════════════════════════════════════════════════

Read these files BEFORE starting:
1. agents/briefs/BACKEND.md (your role and file ownership)
2. docs/sprint-4-multi.md (Sprint 4 details)
3. docs/api-contracts.md (API specification - YOUR SOURCE OF TRUTH)
4. docs/WORKFLOW.md (multi-agent protocol)
5. docs/architecture.md (system design)
6. services/backtest/models.py (BacktestResult, PerformanceMetrics to return)
7. packages/common/schemas.py (existing data models)

═══════════════════════════════════════════════════════════════
📋 YOUR TASKS
═══════════════════════════════════════════════════════════════

Task A1: Create FastAPI App Structure
- Create services/api/ directory
- Create services/api/pyproject.toml (deps: fastapi, uvicorn, pydantic)
- Create services/api/main.py:
  - FastAPI app with title, version
  - CORS middleware
  - Include routers for each domain
- Create services/api/__init__.py

Task A2: Implement Metrics Endpoint
- Create services/api/routers/metrics.py
- Implement: GET /v1/metrics/summary
  - Query params: period (1d, 1w, 1m, 3m, 1y, all), mode (PAPER, LIVE)
  - Returns: total_pnl, sharpe_ratio, max_drawdown, win_rate, equity_curve
  - Reference: docs/api-contracts.md "Metrics & Summary" section

Task A3: Implement Strategies Endpoints
- Create services/api/routers/strategies.py
- Implement:
  - GET /v1/strategies - List all strategies
  - GET /v1/strategies/{strategy_id} - Get strategy detail
  - PATCH /v1/strategies/{strategy_id} - Update strategy config
- Reference: docs/api-contracts.md "Strategies" section

Task A4: Implement Runs Endpoints (CRITICAL for Dashboard)
- Create services/api/routers/runs.py
- Implement:
  - GET /v1/runs - List backtest runs
  - GET /v1/runs/{run_id} - Get run detail with full results
  - POST /v1/runs - Trigger new backtest
- This is what the dashboard will display!
- Returns: BacktestResult from services/backtest/models.py
- Reference: docs/api-contracts.md "Runs" section

Task A5: Implement Positions Endpoints
- Create services/api/routers/positions.py
- Implement:
  - GET /v1/positions - List current positions
  - GET /v1/positions/{position_id} - Position detail
- Reference: docs/api-contracts.md "Positions" section

Task A6: Implement Health Endpoint
- Create services/api/routers/health.py
- Implement: GET /v1/health
- Returns: status, service health (database, redis, broker)
- Reference: docs/api-contracts.md "System Health" section

Task A7: Wire to Database
- Create services/api/dependencies.py
- Create database session dependency
- Import models from services/data/models.py (don't modify!)
- Query database for actual data
- For backtests: Read from services/backtest or store results in DB

Task A8: Create Response Models
- Create packages/common/api_schemas.py (or update existing)
- Define Pydantic models matching docs/api-contracts.md responses:
  - MetricsSummaryResponse
  - StrategyResponse, StrategyListResponse
  - RunResponse, RunListResponse
  - PositionResponse, PositionListResponse
  - HealthResponse

Task A9: Documentation
- Create services/api/README.md with:
  - Setup instructions
  - How to run: uvicorn main:app --reload
  - Endpoint summary
  - Example requests/responses

═══════════════════════════════════════════════════════════════
🚫 FILE OWNERSHIP BOUNDARIES
═══════════════════════════════════════════════════════════════

✅ YOU CAN EDIT:
- services/api/**/*.py (all files)
- services/api/README.md
- services/api/pyproject.toml
- packages/common/api_schemas.py (response models)

❌ YOU CANNOT EDIT:
- services/data/models.py (Data Agent owns - import, don't modify)
- services/data/alembic/** (Data Agent owns migrations)
- services/backtest/**/*.py (Sprint 3 code - use it, don't modify)
- apps/dashboard/** (Frontend Agent owns)
- docker-compose.yml (DevOps Agent owns)
- tests/** (QA Agent owns)

COORDINATION POINTS:
- Use Data Agent's models: from services.data.models import ...
- Use Backtest models: from services.backtest.models import BacktestResult
- If you need new DB tables → Coordinate with Data Agent

═══════════════════════════════════════════════════════════════
✅ ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

Functional:
- [ ] All endpoints respond with valid JSON
- [ ] Response format matches docs/api-contracts.md EXACTLY
- [ ] GET /v1/runs/{id} returns full backtest results
- [ ] Error responses use consistent format
- [ ] OpenAPI docs available at /docs

Technical:
- [ ] Code follows @python-patterns skill
- [ ] Code follows @api-patterns skill
- [ ] Code follows @clean-code skill
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] Pydantic models for all request/response

Performance:
- [ ] Endpoints respond in < 500ms

═══════════════════════════════════════════════════════════════
📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

When complete, provide:

1. Implementation Summary
   - Endpoints implemented
   - Design decisions made

2. Files Created/Modified
   - List all files with brief description

3. Skill Evidence
   - @python-patterns checklist: X/Y completed
   - @api-patterns checklist: X/Y completed
   - @clean-code checklist: X/Y completed

4. How to Test
   - Start command: cd services/api && poetry run uvicorn main:app --reload
   - Example curl commands for each endpoint
   - OpenAPI docs URL

5. Known Issues/Limitations
   - Any TODOs
   - Any mock data used

═══════════════════════════════════════════════════════════════
🚨 RED FLAGS - STOP IF YOU SEE THESE
═══════════════════════════════════════════════════════════════

- Editing services/data/models.py → Data Agent owns that
- Editing apps/dashboard/** → Frontend Agent owns that
- Writing tests → QA Agent owns that
- Modifying docker-compose.yml → DevOps Agent owns that
- Response format not matching api-contracts.md → Fix it
- Skipping skill invocation → Mandatory before coding
- Functions > 20 lines → Split them

═══════════════════════════════════════════════════════════════
```

---

## 🖥️ Frontend Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the Frontend Agent for Sprint 4: Dashboard & API.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY CODING
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills
You MUST invoke these skills before coding:

1. @nextjs-best-practices
   - Read: agents/skills/skills/nextjs-best-practices/SKILL.md
   - Purpose: App Router, Server Components, data fetching
   - Checklist:
     - [ ] Using Next.js 14 App Router (not pages/)
     - [ ] Server Components by default, Client only when needed
     - [ ] Using loading.tsx and error.tsx files
     - [ ] Proper metadata configuration
     - [ ] Using route groups for organization

2. @react-patterns
   - Read: agents/skills/skills/react-patterns/SKILL.md
   - Purpose: Component design, hooks, state management
   - Checklist:
     - [ ] One responsibility per component
     - [ ] Props down, events up
     - [ ] Using React Query or SWR for server state
     - [ ] Custom hooks for reusable logic
     - [ ] Proper error boundaries

3. @tailwind-patterns
   - Read: agents/skills/skills/tailwind-patterns/SKILL.md
   - Purpose: Styling, responsive design, dark mode
   - Checklist:
     - [ ] Mobile-first responsive design
     - [ ] Dark mode support (class-based)
     - [ ] Using Tailwind CSS v4 patterns
     - [ ] Component extraction when needed
     - [ ] Semantic color naming

4. @clean-code
   - Read: agents/skills/skills/clean-code/SKILL.md
   - Purpose: Code quality
   - Checklist:
     - [ ] Small, focused components
     - [ ] Clear naming conventions
     - [ ] No magic numbers

STEP 3: Mark Skill Checklists Complete
Before coding, mark each checklist item as complete or explain why N/A.

IF SKILLS CANNOT BE INVOKED: STOP and explain why.

═══════════════════════════════════════════════════════════════
📚 CONTEXT READING
═══════════════════════════════════════════════════════════════

Read these files BEFORE starting:
1. docs/sprint-4-multi.md (Sprint 4 details)
2. docs/dashboard-spec.md (Dashboard specification - YOUR SOURCE OF TRUTH)
3. docs/api-contracts.md (API you will fetch from)
4. docs/WORKFLOW.md (multi-agent protocol)

═══════════════════════════════════════════════════════════════
📋 YOUR TASKS
═══════════════════════════════════════════════════════════════

Task B1: Initialize Next.js 14 Project
- Create apps/dashboard/ directory
- Run: npx create-next-app@latest . --typescript --tailwind --eslint --app
- Configure:
  - TypeScript strict mode
  - Path aliases (@/)
  - App Router structure

Task B2: Setup UI Components
- Install Shadcn/UI: npx shadcn@latest init
- Add components:
  - Button, Card, Table
  - Tabs, Dialog
  - Input, Select
  - Skeleton (loading states)
- Configure dark mode (class-based)

Task B3: Create Layout Shell
- Create app/layout.tsx:
  - Dark theme by default
  - Inter font
  - Global styles
- Create app/(dashboard)/layout.tsx:
  - Sidebar navigation (pages: Overview, Strategies, Runs, Health)
  - Header with user menu
  - Mobile responsive (collapsible sidebar)

Task B4: Build Overview Page (/)
- Create app/(dashboard)/page.tsx
- Components:
  - Stats cards (Total P&L, Sharpe, Drawdown, Win Rate)
  - Equity curve chart (use Recharts or TradingView Lightweight)
  - Active alerts widget
  - Quick actions (Kill Switch button - UI only)
- Data: Fetch from GET /v1/metrics/summary
- Reference: docs/dashboard-spec.md "Overview Page"

Task B5: Build Strategies Page (/strategies)
- Create app/(dashboard)/strategies/page.tsx
- Components:
  - Strategy table (Name, Status, Mode, Performance, Actions)
  - Status badges (Live=green, Paper=yellow, Stopped=red)
  - Filter by status
  - Actions: Pause, Config, View
- Data: Fetch from GET /v1/strategies
- Reference: docs/dashboard-spec.md "Strategies Page"

Task B6: Build Strategy Detail (/strategies/[id])
- Create app/(dashboard)/strategies/[id]/page.tsx
- Components:
  - Performance chart
  - Configuration display
  - Recent trades table
  - Edit configuration modal
- Data: Fetch from GET /v1/strategies/{id}

Task B7: Build Runs Page (/runs)
- Create app/(dashboard)/runs/page.tsx
- Components:
  - Runs table (ID, Type, Date, Strategy, Result, Report link)
  - Filter by run_type (BACKTEST, PAPER, LIVE)
  - "New Backtest" button + modal
- Data: Fetch from GET /v1/runs

Task B8: Build Run Detail Page (/runs/[id])
- Create app/(dashboard)/runs/[id]/page.tsx
- Components:
  - Full backtest report display
  - Equity curve chart
  - Trade list table
  - Performance metrics cards
  - Export options (JSON, HTML)
- Data: Fetch from GET /v1/runs/{id}
- THIS IS CRITICAL: Display Sprint 3 backtest results!

Task B9: Build Health Page (/health)
- Create app/(dashboard)/health/page.tsx
- Components:
  - Service status grid
  - API latency display
  - Data feed status
  - Last updated timestamp
- Data: Fetch from GET /v1/health

Task B10: Setup API Client
- Create lib/api.ts:
  - Base URL configuration
  - Typed fetch functions for each endpoint
  - Error handling
- Create lib/hooks/:
  - useMetrics()
  - useStrategies()
  - useRuns()
  - useHealth()
- Use React Query or SWR for caching and polling

Task B11: Loading & Error States
- Create loading.tsx for each route
- Create error.tsx for error boundaries
- Use Skeleton components for loading states

Task B12: Documentation
- Create apps/dashboard/README.md:
  - Setup instructions (npm install, npm run dev)
  - Environment variables needed
  - Project structure overview

═══════════════════════════════════════════════════════════════
🚫 FILE OWNERSHIP BOUNDARIES
═══════════════════════════════════════════════════════════════

✅ YOU CAN EDIT:
- apps/dashboard/**
- apps/dashboard/package.json
- apps/dashboard/README.md
- apps/dashboard/.env.local.example

❌ YOU CANNOT EDIT:
- services/**/*.py (Backend Agent)
- docker-compose.yml (DevOps Agent)
- tests/** (QA Agent)
- docs/*.md (Architect Agent for updates)

COORDINATION POINTS:
- API endpoint URLs from Backend Agent
- May need to wait for Backend Agent to complete for Task B10

═══════════════════════════════════════════════════════════════
✅ ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

Functional:
- [ ] Dashboard loads at localhost:3000
- [ ] Overview page displays metrics and equity curve
- [ ] Strategies page lists strategies with filters
- [ ] Runs page shows backtest history
- [ ] Run detail page displays full backtest report
- [ ] Health page shows system status

Technical:
- [ ] Code follows @nextjs-best-practices skill
- [ ] Code follows @react-patterns skill
- [ ] Code follows @tailwind-patterns skill
- [ ] Code follows @clean-code skill
- [ ] TypeScript strict mode, no errors
- [ ] Responsive design (mobile and desktop)
- [ ] Dark mode works

Performance:
- [ ] Initial page load < 3s
- [ ] No console errors

═══════════════════════════════════════════════════════════════
📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

When complete, provide:

1. Implementation Summary
   - Pages created
   - Components built
   - Design decisions

2. Files Created
   - List all files with brief description

3. Skill Evidence
   - @nextjs-best-practices checklist: X/Y completed
   - @react-patterns checklist: X/Y completed
   - @tailwind-patterns checklist: X/Y completed
   - @clean-code checklist: X/Y completed

4. How to Run
   - Setup: cd apps/dashboard && npm install
   - Dev: npm run dev
   - Environment variables needed

5. Known Issues/Limitations
   - Any mock data used
   - Any features deferred

═══════════════════════════════════════════════════════════════
🚨 RED FLAGS - STOP IF YOU SEE THESE
═══════════════════════════════════════════════════════════════

- Editing services/**/*.py → Backend Agent owns that
- Writing Python code → You only write TypeScript/React
- Skipping skill invocation → Mandatory before coding
- Using Pages Router instead of App Router → Use App Router
- Not implementing loading/error states → Required
- Hardcoding API URL → Use environment variable

═══════════════════════════════════════════════════════════════
```

---

## 🏗️ Architect Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the Architect Agent for Sprint 4: Dashboard & API.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY WORK
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills

1. @api-patterns
   - Read: agents/skills/skills/api-patterns/SKILL.md
   - Purpose: Validate API design against best practices
   - Checklist:
     - [ ] RESTful resource naming
     - [ ] Consistent response format
     - [ ] Proper status codes
     - [ ] Pagination for lists
     - [ ] Error handling

IF SKILLS CANNOT BE INVOKED: Document which skills were attempted and proceed.

═══════════════════════════════════════════════════════════════
📚 CONTEXT READING
═══════════════════════════════════════════════════════════════

Read these files BEFORE starting:
1. agents/briefs/ARCHITECT.md (your role)
2. docs/sprint-4-multi.md (Sprint 4 details)
3. docs/api-contracts.md (API specification to validate)
4. docs/architecture.md (current architecture)
5. docs/WORKFLOW.md (multi-agent protocol)
6. services/api/** (Backend Agent's implementation - review)
7. apps/dashboard/** (Frontend Agent's implementation - review)

WAIT FOR: Backend Agent and Frontend Agent to make progress. Review as work completes.

═══════════════════════════════════════════════════════════════
📋 YOUR TASKS
═══════════════════════════════════════════════════════════════

Task C1: Validate API Implementation
- Compare Backend Agent's implementation to docs/api-contracts.md
- Check:
  - Endpoint paths match
  - Request/response schemas match
  - Status codes match
  - Error format matches
- Document any deviations

Task C2: Update Architecture Documentation
- Update docs/architecture.md:
  - Add API Service section (services/api)
  - Document endpoint summary
  - Add data flow: API → Database → Dashboard
  - Component diagram (text or mermaid)

Task C3: Document Dashboard Integration
- Update docs/architecture.md:
  - Add Dashboard section (apps/dashboard)
  - Document data flow: Dashboard → API → Services
  - Technology stack summary

Task C4: Create ADR (if needed)
- If significant decisions were made:
  - Create adr/0006-api-architecture.md
  - Document: REST vs GraphQL choice
  - Document: Polling vs WebSocket for dashboard
  - Document: Authentication approach

Task C5: Validate Data Contracts
- Ensure API responses align with docs/data-contracts.md
- Verify type consistency across system

═══════════════════════════════════════════════════════════════
🚫 FILE OWNERSHIP BOUNDARIES
═══════════════════════════════════════════════════════════════

✅ YOU CAN EDIT:
- docs/architecture.md (updates)
- docs/api-contracts.md (corrections if needed)
- adr/*.md (new ADRs)

❌ YOU CANNOT EDIT:
- services/**/*.py (Backend Agent)
- apps/dashboard/** (Frontend Agent)
- tests/** (QA Agent)
- docker-compose.yml (DevOps Agent)

═══════════════════════════════════════════════════════════════
✅ ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

- [ ] API implementation validated against contracts
- [ ] docs/architecture.md updated with API and Dashboard sections
- [ ] Data flow documented
- [ ] ADR created (if significant decisions)
- [ ] No code files edited

═══════════════════════════════════════════════════════════════
📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

When complete, provide:

1. API Validation Summary
   - Endpoints validated
   - Deviations found (if any)
   - Recommendations

2. Documentation Updates
   - Changes to docs/architecture.md
   - New ADR (if created)

3. Design Review
   - API design quality assessment
   - Dashboard design quality assessment
   - Integration concerns (if any)

4. Recommendations
   - Future improvements
   - Technical debt identified

═══════════════════════════════════════════════════════════════
🚨 RED FLAGS - STOP IF YOU SEE THESE
═══════════════════════════════════════════════════════════════

- Writing code in services/** → Backend Agent owns that
- Creating React components → Frontend Agent owns that
- Skipping skill invocation → Mandatory
- Not reading Backend/Frontend output → Must review

═══════════════════════════════════════════════════════════════
```

---

## 🧪 QA Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the QA Agent for Sprint 4: Dashboard & API.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY WORK
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills

1. @testing-patterns
   - Read: agents/skills/skills/testing-patterns/SKILL.md
   - Purpose: Test design, factory functions, TDD
   - Checklist:
     - [ ] Test behavior, not implementation
     - [ ] Factory functions for test data
     - [ ] Descriptive test names
     - [ ] Clear mock between tests
     - [ ] One behavior per test

2. @python-patterns
   - Read: agents/skills/skills/python-patterns/SKILL.md
   - Purpose: Python test code
   - Checklist:
     - [ ] Use pytest fixtures
     - [ ] Type hints on test helpers
     - [ ] Clear test structure

STEP 3: Mark Skill Checklists Complete

IF SKILLS CANNOT BE INVOKED: STOP and explain why.

═══════════════════════════════════════════════════════════════
📚 CONTEXT READING
═══════════════════════════════════════════════════════════════

Read these files BEFORE starting:
1. agents/briefs/QA.md (your role)
2. docs/sprint-4-multi.md (Sprint 4 details)
3. docs/api-contracts.md (API to test against)
4. docs/WORKFLOW.md (multi-agent protocol)
5. services/api/** (Backend Agent's implementation - test this)

WAIT FOR: Backend Agent must complete implementation first.

═══════════════════════════════════════════════════════════════
📋 YOUR TASKS
═══════════════════════════════════════════════════════════════

Task D1: Write API Unit Tests
Create services/api/test_metrics.py:
- Test GET /v1/metrics/summary
- Test query parameter handling (period, mode)
- Test response format matches api-contracts.md

Create services/api/test_strategies.py:
- Test GET /v1/strategies
- Test GET /v1/strategies/{id}
- Test PATCH /v1/strategies/{id}
- Test 404 for unknown strategy

Create services/api/test_runs.py:
- Test GET /v1/runs
- Test GET /v1/runs/{id}
- Test POST /v1/runs (trigger backtest)
- Test response includes full BacktestResult

Create services/api/test_health.py:
- Test GET /v1/health
- Test response format

Task D2: Write Integration Tests
Create tests/integration/test_api_e2e.py:
- Full flow: Create backtest → Get results → Verify data
- Test API responses with real database
- Test error handling

Task D3: Create Test Fixtures
Create tests/fixtures/api_data.py:
- get_mock_strategy()
- get_mock_backtest_run()
- get_mock_metrics()
- get_mock_position()
- Sample API responses

Task D4: Create Verification Runbook
Create docs/runbooks/api-verification.md:
- How to verify API functionality
- Manual test procedures
- Example curl commands
- Expected responses
- Troubleshooting guide

═══════════════════════════════════════════════════════════════
🚫 FILE OWNERSHIP BOUNDARIES
═══════════════════════════════════════════════════════════════

✅ YOU CAN EDIT:
- services/api/test_*.py
- tests/integration/test_api_*.py
- tests/fixtures/api_data.py
- docs/runbooks/api-verification.md

❌ YOU CANNOT EDIT:
- services/api/**/*.py (implementation - Backend Agent)
- apps/dashboard/** (Frontend Agent)
- docker-compose.yml (DevOps Agent)

═══════════════════════════════════════════════════════════════
✅ ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

- [ ] All API tests pass: poetry run pytest services/api/test_*.py
- [ ] Integration test passes: poetry run pytest tests/integration/test_api_e2e.py
- [ ] Test coverage for critical paths
- [ ] Runbook created
- [ ] Tests follow @testing-patterns skill

═══════════════════════════════════════════════════════════════
📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

When complete, provide:

1. Test Summary
   - Tests written
   - Tests passing/failing
   - Coverage areas

2. Test Files Created
   - List all test files

3. Skill Evidence
   - @testing-patterns checklist: X/Y completed
   - @python-patterns checklist: X/Y completed

4. Runbook Location
   - docs/runbooks/api-verification.md

5. How to Run Tests
   - Command: poetry run pytest services/api/
   - Command: poetry run pytest tests/integration/

═══════════════════════════════════════════════════════════════
🚨 RED FLAGS - STOP IF YOU SEE THESE
═══════════════════════════════════════════════════════════════

- Editing services/api/main.py → Backend Agent owns that
- Writing implementation code → QA only writes tests
- Skipping skill invocation → Mandatory
- Testing implementation details → Test behavior only

═══════════════════════════════════════════════════════════════
```

---

## 🔧 DevOps Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the DevOps Agent for Sprint 4: Dashboard & API.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY WORK
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

═══════════════════════════════════════════════════════════════
📚 CONTEXT READING
═══════════════════════════════════════════════════════════════

Read these files BEFORE starting:
1. agents/briefs/DEVOPS.md (your role)
2. docs/sprint-4-multi.md (Sprint 4 details)
3. docs/architecture.md (system design)
4. docker-compose.yml (current setup)

═══════════════════════════════════════════════════════════════
📋 YOUR TASKS
═══════════════════════════════════════════════════════════════

Task E1: Add API Service to Docker Compose
- Update docker-compose.yml:
  - Add 'api' service
  - Base image: Python 3.11
  - Working dir: /app/services/api
  - Command: uvicorn main:app --host 0.0.0.0 --port 8000
  - Ports: 8000:8000
  - Depends on: db, redis
  - Health check

Task E2: Add Environment Variables
- Update configs/environments/.env.example:
  - API_HOST=0.0.0.0
  - API_PORT=8000
  - CORS_ORIGINS=http://localhost:3000
  - JWT_SECRET=your_secret_here (placeholder)

Task E3: Create Dashboard Environment Example
- Create apps/dashboard/.env.local.example:
  - NEXT_PUBLIC_API_URL=http://localhost:8000/v1

Task E4: Update Scripts
- Update Makefile or scripts/:
  - make api-dev: Start API in dev mode
  - make dashboard-dev: Start dashboard in dev mode
  - make dev: Start both

Task E5: Verify Docker Setup
- Test: docker-compose up -d
- Verify: All services healthy
- Test: API accessible at localhost:8000/docs

═══════════════════════════════════════════════════════════════
🚫 FILE OWNERSHIP BOUNDARIES
═══════════════════════════════════════════════════════════════

✅ YOU CAN EDIT:
- docker-compose.yml
- configs/environments/.env.example
- apps/dashboard/.env.local.example
- Makefile, scripts/**
- .github/workflows/** (if CI needed)

❌ YOU CANNOT EDIT:
- services/**/*.py (Backend Agent)
- apps/dashboard/src/** (Frontend Agent)
- tests/** (QA Agent)

═══════════════════════════════════════════════════════════════
✅ ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

- [ ] docker-compose up starts API service
- [ ] API accessible at localhost:8000
- [ ] Health check passes
- [ ] Environment variables documented
- [ ] No secrets committed

═══════════════════════════════════════════════════════════════
📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

When complete, provide:

1. Docker Updates
   - Changes to docker-compose.yml
   - New services added

2. Environment Variables
   - New variables added
   - Documentation

3. Scripts Added
   - New make targets or scripts

4. Verification
   - docker-compose up -d works
   - Services healthy

═══════════════════════════════════════════════════════════════
🚨 RED FLAGS - STOP IF YOU SEE THESE
═══════════════════════════════════════════════════════════════

- Writing Python application code → Backend Agent owns that
- Writing React code → Frontend Agent owns that
- Committing .env with secrets → Use .env.example only

═══════════════════════════════════════════════════════════════
```

---

## 🔄 Integrator Prompt

**Run this in Composer 1 AFTER all agents complete:**

---

```
You are the Integrator for Sprint 4: Dashboard & API.

═══════════════════════════════════════════════════════════════
📚 CONTEXT READING
═══════════════════════════════════════════════════════════════

Read:
1. docs/sprint-4-multi.md (Sprint 4 requirements)
2. Backend Agent's output summary
3. Frontend Agent's output summary
4. Architect Agent's output summary
5. QA Agent's output summary
6. DevOps Agent's output summary

═══════════════════════════════════════════════════════════════
📋 YOUR TASKS
═══════════════════════════════════════════════════════════════

Task 1: Merge Agent Outputs
- Verify file ownership boundaries respected
- Ensure no conflicts between agents
- Check that no agent edited files outside their ownership

Task 2: Verify API Works
- Start API: cd services/api && poetry run uvicorn main:app --reload
- Test: curl http://localhost:8000/v1/health
- Test: curl http://localhost:8000/v1/runs
- Verify: OpenAPI docs at http://localhost:8000/docs

Task 3: Verify Dashboard Works
- Start Dashboard: cd apps/dashboard && npm run dev
- Test: Open http://localhost:3000
- Verify: Overview page loads
- Verify: Strategies page lists strategies
- Verify: Runs page shows backtests

Task 4: Verify Integration
- Dashboard fetches data from API
- Backtest results visible in dashboard
- No console errors

Task 5: Run QA Tests
- API tests: poetry run pytest services/api/
- Integration tests: poetry run pytest tests/integration/

Task 6: Verify Sprint 4 Completion
Check all acceptance criteria from docs/sprint-4-multi.md:

Functional:
- [ ] API endpoints respond correctly
- [ ] Dashboard displays data
- [ ] Integration works (dashboard → API)

Technical:
- [ ] Code follows skills
- [ ] Tests pass

Documentation:
- [ ] services/api/README.md exists
- [ ] apps/dashboard/README.md exists
- [ ] docs/architecture.md updated

Task 7: Update Progress
- Mark Sprint 4 tasks complete in plans/task_plan.md
- Update plans/progress.md
- Create SPRINT4_SUMMARY.md

═══════════════════════════════════════════════════════════════
📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

1. Merge Summary
   - Files from each agent
   - Conflicts resolved (if any)
   - Ownership boundaries verified

2. API Verification Results
   - Endpoints tested
   - Pass/Fail status

3. Dashboard Verification Results
   - Pages tested
   - Pass/Fail status

4. Integration Verification
   - Dashboard → API connection
   - Data display working

5. Test Results
   - API tests: X passed, Y failed
   - Integration tests: Pass/Fail

6. Acceptance Criteria Status
   - Functional: X/Y met
   - Technical: X/Y met
   - Documentation: X/Y met

7. Sprint 4 Completion Confirmation
   - ✅ Sprint 4 Complete OR
   - ⚠️ Sprint 4 Incomplete (list remaining items)

═══════════════════════════════════════════════════════════════
```

---

## ✅ Task Coverage Verification

**All Sprint 4 Tasks Covered:**

| Task | Agent | Status |
|------|-------|--------|
| FastAPI App Structure | Backend | ✅ Assigned |
| Metrics Endpoint | Backend | ✅ Assigned |
| Strategies Endpoints | Backend | ✅ Assigned |
| Runs Endpoints | Backend | ✅ Assigned |
| Positions Endpoints | Backend | ✅ Assigned |
| Health Endpoint | Backend | ✅ Assigned |
| Response Models | Backend | ✅ Assigned |
| Next.js Setup | Frontend | ✅ Assigned |
| UI Components | Frontend | ✅ Assigned |
| Layout Shell | Frontend | ✅ Assigned |
| Overview Page | Frontend | ✅ Assigned |
| Strategies Page | Frontend | ✅ Assigned |
| Runs Page | Frontend | ✅ Assigned |
| Run Detail Page | Frontend | ✅ Assigned |
| Health Page | Frontend | ✅ Assigned |
| API Client | Frontend | ✅ Assigned |
| API Tests | QA | ✅ Assigned |
| Integration Tests | QA | ✅ Assigned |
| Test Fixtures | QA | ✅ Assigned |
| Runbook | QA | ✅ Assigned |
| API Validation | Architect | ✅ Assigned |
| Architecture Docs | Architect | ✅ Assigned |
| Docker Updates | DevOps | ✅ Assigned |
| Environment Vars | DevOps | ✅ Assigned |

**All tasks from `plans/task_plan.md` Sprint 4 section are covered.**

---

**Ready for Execution:** Copy each agent prompt to separate Composer tabs and run in parallel (Backend, Frontend, DevOps, Architect can start immediately; QA starts after Backend).
