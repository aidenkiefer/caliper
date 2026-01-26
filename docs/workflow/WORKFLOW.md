# Multi-Agent Workflow Guide

**This is the mandatory entrypoint for all Cursor agents working on this project.**

## 🎯 Purpose

This document defines how multiple Composer instances work together in parallel to maximize speed and minimize rework. Each agent has a specific role, scope, and output contract.

---

## 📋 Skill Invocation Rules

**CRITICAL:** Before any coding, you MUST invoke relevant skills.

### Skill Priority Order

1. **Process Skills First** (determine HOW to approach)
   - `@using-superpowers` - Always check this first
   - `@writing-plans` - For planning/sprint breakdown
   - `@testing-patterns` - For test design

2. **Domain Skills Second** (guide execution)
   - `@python-patterns` - Python code (services/*)
   - `@postgres-best-practices` - Database work
   - `@database-design` - Schema design
   - `@api-patterns` - FastAPI endpoints
   - `@clean-code` - Code quality
   - `@testing-patterns` - Test implementation

### Skill Invocation Protocol

```
1. Read task description
2. Check: "Might any skill apply?" (even 1% chance = YES)
3. Invoke Skill tool: @skill-name
4. Announce: "Using [skill] to [purpose]"
5. If skill has checklist → Create TodoWrite todos per item
6. Follow skill exactly
7. After completion → Audit: "Completed skill steps: X/Y"
```

**Red Flags (STOP if you think these):**
- "This is simple, I don't need a skill"
- "Let me explore first, then check skills"
- "I remember this skill from before"

**Rule:** Skills are mandatory, not optional. If a skill exists for your domain, use it.

---

## 🏃 Sprint Execution Protocol

### Phase 1: Orchestrator (Composer 1)

**Role:** Sprint Planner + Agent Spawner

**Steps:**
1. Read context:
   - `docs/floorplan.md`
   - `docs/research.md`
   - `docs/architecture.md`
   - `plans/task_plan.md` (current sprint)
   - `adr/*.md` (architectural decisions)
   - `agents/skills/skills/using-superpowers/SKILL.md`

2. Generate Sprint Plan:
   - Break sprint into 4-5 parallelizable tasks
   - Identify dependencies
   - Map tasks to agents (Architect, Backend, Data, DevOps, QA)

3. Create Agent Prompts:
   - For each agent, output a copy-pastable prompt including:
     - Agent brief to read (`agents/briefs/X.md`)
     - Exact task list
     - File ownership boundaries
     - Required skills to invoke
     - Acceptance criteria
     - Output format

4. Provide Integrator Prompt:
   - Final merge pass instructions
   - Consistency checks
   - Documentation updates

### Phase 2: Parallel Agents (Composer 2-6)

**Execution Model:** Multiple Composer tabs/threads running simultaneously

**Agent Types:**
- **Architect** - Endpoint design, data flow, naming conventions
- **Backend** - FastAPI services, business logic
- **Data** - SQLAlchemy models, Alembic migrations, TimescaleDB setup
- **DevOps** - Docker, env vars, scripts, networking
- **QA** - Unit tests, integration tests, runbooks

**Each Agent Must:**
1. Read their brief (`agents/briefs/X.md`)
2. Invoke required skills BEFORE coding
3. Only edit files in their ownership map
4. Produce outputs matching the contract
5. Provide "Skill Evidence" (checklist completion audit)

### Phase 3: Integrator (Composer 1, after agents)

**Role:** Merge + Validate + Document

**Steps:**
1. Resolve file conflicts (if any)
2. Run acceptance tests for each agent
3. Check consistency across agents
4. Update documentation
5. Mark sprint tasks complete in `plans/task_plan.md`

---

## 📦 Output Contracts (Per Sprint)

### Sprint 1: Infrastructure & Data
- **Data Agent:** SQLAlchemy models, Alembic migration, TimescaleDB hypertables
- **DevOps Agent:** `docker-compose.yml`, `.env.example`, startup scripts
- **Backend Agent:** `services/data` skeleton, `AlpacaProvider` class
- **QA Agent:** Basic DB connection test, migration test

### Sprint 2: Feature Pipeline & Strategy Core
- **Backend Agent:** `services/features` pipeline, indicator calculators
- **Backend Agent:** `packages/strategies` base class, SMA crossover strategy
- **QA Agent:** Indicator unit tests, strategy signal tests

### Sprint 3: Backtesting & Reporting
- **Backend Agent:** `services/backtest` engine, report generation
- **QA Agent:** Backtest integration test, P&L validation test

### Sprint 4: Dashboard & API
- **Backend Agent:** FastAPI endpoints (`services/api`), database queries
- **Architect Agent:** API contract validation, endpoint design review
- **Frontend Agent:** Next.js app (`apps/dashboard`), pages/components
- **QA Agent:** API integration tests, dashboard smoke tests

### Sprint 5: Execution & Risk
- **Backend Agent:** `services/execution` broker client, `services/risk` guardrails
- **QA Agent:** Risk limit tests, kill switch tests, execution integration tests

---

## 🚫 File Ownership Boundaries

**CRITICAL:** Agents must NOT edit files outside their ownership.

### Architect Agent
- `docs/api-contracts.md` (updates only)
- `docs/architecture.md` (updates only)
- No code files

### Backend Agent
- `services/api/**`
- `services/features/**`
- `services/backtest/**`
- `services/execution/**`
- `services/risk/**`
- `packages/strategies/**`
- `packages/models/**`

### Data Agent
- `services/data/models.py`
- `services/data/alembic/**`
- `services/data/database.py`
- `services/data/providers/**`

### DevOps Agent
- `docker-compose.yml`
- `configs/environments/.env.example`
- `Makefile` or `scripts/**`
- `.github/workflows/**` (CI/CD)

### QA Agent
- `tests/**`
- `services/*/test_*.py`
- `packages/*/test_*.py`
- `docs/runbooks/**`

### Frontend Agent (Sprint 4+)
- `apps/dashboard/**`
- `package.json` (dashboard workspace)

---

## ✅ Acceptance Criteria Format

Each agent must provide:

```markdown
## Acceptance Criteria

### Functional
- [ ] Feature X works (describe test)
- [ ] Feature Y works (describe test)

### Technical
- [ ] Code follows @python-patterns skill
- [ ] Tests pass: `poetry run pytest`
- [ ] No linter errors

### Documentation
- [ ] Updated relevant docs
- [ ] Added runbook entries (if applicable)
```

---

## 🔄 Handoff Protocol

**Between Agents:**
1. Agent completes their task
2. Agent outputs: "✅ [Agent Name] Complete"
3. Agent lists: Files changed, Tests added, Docs updated
4. Next agent reads previous agent's outputs

**To Integrator:**
1. All agents complete
2. Each agent provides summary
3. Integrator merges and validates
4. Integrator updates `plans/task_plan.md`

---

## 📚 Reference Documents

- **Skills Catalog:** `agents/skills/skills/`
- **Agent Briefs:** `agents/briefs/*.md`
- **Architecture:** `docs/architecture.md`
- **Data Contracts:** `docs/data-contracts.md`
- **API Contracts:** `docs/api-contracts.md`
- **Sprint Plan:** `plans/task_plan.md`
- **ADRs:** `adr/*.md`

---

## 🎬 Quick Start: Running Multi-Agent Sprint

1. **Open Composer 1** → Paste Orchestrator Prompt (see below)
2. **Copy Agent Prompts** → Open Composer 2-6, paste one prompt each
3. **Run in parallel** → Each agent works independently
4. **Integrator merges** → Composer 1 runs final pass

**Orchestrator Prompt Template:**

```
You are the Sprint Orchestrator for the Quant ML Trading Platform.

Read:
- docs/WORKFLOW.md (this file)
- plans/task_plan.md (current sprint)
- agents/briefs/*.md (all agent briefs)

Goal: Complete Sprint N using multi-agent parallel workflow.

Steps:
1. Generate Sprint Plan (tasks, dependencies, parallelization)
2. Create Agent Prompts (Architect, Backend, Data, DevOps, QA)
3. Provide Integrator Prompt

Output format:
1) Sprint Plan
2) Agent Prompts (one per agent)
3) Integrator Prompt
```

---

## ⚠️ Enforcement Rules

1. **Skills are mandatory** - No exceptions
2. **File boundaries are strict** - No cross-agent edits
3. **Acceptance tests are required** - Each agent must provide tests
4. **Documentation updates are mandatory** - Code without docs is incomplete

**Violations:** If an agent violates boundaries, Integrator must reject and request rework.
