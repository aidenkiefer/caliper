# Multi-Agent Workflow Quick Start

**Quick reference for running parallel agents in Cursor Composer.**

---

## 🎯 The Setup

**Composer 1 = Orchestrator** (plans, spawns agents, integrates)  
**Composer 2-6 = Agents** (Architect, Backend, Data, DevOps, QA)

---

## ⚡ Fast Setup (5 Minutes)

### Step 1: Orchestrator (Composer 1)

Paste this prompt:

```
You are the Sprint Orchestrator for the Quant ML Trading Platform.

Read:
- docs/WORKFLOW.md
- plans/task_plan.md (current sprint)
- agents/briefs/*.md

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

### Step 2: Copy Agent Prompts

Orchestrator will output prompts like:

```
=== BACKEND AGENT PROMPT ===
[Copy this entire section]
```

### Step 3: Open Multiple Composer Tabs

- **Tab 1:** Orchestrator (already running)
- **Tab 2:** Backend Agent → Paste Backend prompt
- **Tab 3:** Data Agent → Paste Data prompt
- **Tab 4:** DevOps Agent → Paste DevOps prompt
- **Tab 5:** QA Agent → Paste QA prompt

### Step 4: Run in Parallel

All agents work simultaneously. Each agent:
1. Reads their brief (`agents/briefs/X.md`)
2. Invokes required skills
3. Edits only their files
4. Produces outputs

### Step 5: Integrator (Composer 1)

After all agents complete, run Integrator prompt:
- Merge outputs
- Resolve conflicts
- Run acceptance tests
- Update documentation

---

## 📋 Agent Roles & Files

| Agent | Owns | Cannot Touch |
|-------|------|--------------|
| **Architect** | `docs/architecture.md`, `docs/api-contracts.md` | Code files |
| **Backend** | `services/api/**`, `services/features/**`, `packages/strategies/**` | DB models, Docker |
| **Data** | `services/data/models.py`, `services/data/alembic/**` | API endpoints, Docker |
| **DevOps** | `docker-compose.yml`, `.env.example`, scripts | Application code |
| **QA** | `tests/**`, `docs/runbooks/**` | Implementation code |

---

## 🛠️ Skills (Mandatory)

**Before coding, agents MUST invoke:**

- `@using-superpowers` - Always first
- `@python-patterns` - Python code
- `@postgres-best-practices` - Database work
- `@api-patterns` - FastAPI endpoints
- `@testing-patterns` - Tests
- `@clean-code` - Code quality

**Rule:** Even 1% chance a skill applies = invoke it.

---

## ✅ Acceptance Criteria Format

Each agent must provide:

```markdown
## ✅ Completion Checklist

- [ ] Read relevant docs
- [ ] Invoked required skills
- [ ] Implemented feature
- [ ] Tests pass
- [ ] Updated documentation
- [ ] No files outside ownership edited
```

---

## 🚨 Common Mistakes

| Mistake | Fix |
|---------|-----|
| Agent edits wrong files | Read `agents/briefs/X.md` file ownership |
| Skills not invoked | Always invoke `@using-superpowers` first |
| No acceptance tests | Each agent must provide tests |
| Documentation not updated | Code without docs is incomplete |

---

## 📚 Reference Files

- **Workflow:** `docs/WORKFLOW.md` (full protocol)
- **Agent Briefs:** `agents/briefs/*.md`
- **Skills:** `agents/skills/skills/`
- **Sprint Plan:** `plans/task_plan.md`

---

## 🎬 Example: Sprint 2 Multi-Agent Run

**Orchestrator Output:**
```
Sprint Plan:
- Backend: Implement feature pipeline
- Backend: Implement strategy framework
- QA: Write tests
- DevOps: (no changes needed)

Agent Prompts:
[Backend Agent Prompt]
[QA Agent Prompt]
```

**Backend Agent:**
- Reads `agents/briefs/BACKEND.md`
- Invokes `@python-patterns`, `@clean-code`
- Implements `services/features/pipeline.py`
- Implements `packages/strategies/sma_crossover.py`
- ✅ Complete

**QA Agent:**
- Reads `agents/briefs/QA.md`
- Invokes `@testing-patterns`
- Writes `services/features/test_*.py`
- Writes `packages/strategies/test_*.py`
- ✅ Complete

**Integrator:**
- Merges outputs
- Runs `poetry run pytest`
- Updates `plans/task_plan.md`
- ✅ Sprint 2 Complete

---

## 💡 Pro Tips

1. **Start with Orchestrator** - Get the plan first
2. **Copy prompts exactly** - Don't modify agent prompts
3. **Check file ownership** - Agents must stay in bounds
4. **Skills are mandatory** - No exceptions
5. **Test as you go** - Don't wait for integration

---

## 🔗 Full Documentation

- **Complete Workflow:** `docs/WORKFLOW.md`
- **Agent Briefs:** `agents/briefs/`
- **Skills Catalog:** `agents/skills/skills/`
