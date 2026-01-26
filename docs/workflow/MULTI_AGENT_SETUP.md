# Multi-Agent Workflow Setup Summary

**Documentation created to enable parallel multi-agent development in Cursor Composer.**

---

## 📁 Files Created

### Core Workflow Documentation

1. **`docs/WORKFLOW.md`** ⭐ **START HERE**
   - Main entrypoint for all agents
   - Skill invocation rules
   - Sprint execution protocol
   - Output contracts per sprint
   - File ownership boundaries
   - Handoff protocols

2. **`docs/MULTI_AGENT_QUICKSTART.md`**
   - Quick reference guide
   - 5-minute setup instructions
   - Common mistakes and fixes
   - Example sprint run

3. **`docs/MULTI_AGENT_SETUP.md`** (this file)
   - Overview of all documentation
   - How files work together

### Agent Briefs

4. **`agents/briefs/ARCHITECT.md`**
   - System design, API contracts
   - Endpoint design, data flow
   - Naming conventions

5. **`agents/briefs/BACKEND.md`**
   - FastAPI services, business logic
   - Feature engineering, strategies
   - Backtesting, execution

6. **`agents/briefs/DATA.md`**
   - Database schemas, SQLAlchemy models
   - Alembic migrations, TimescaleDB
   - Data providers, ingestion

7. **`agents/briefs/DEVOPS.md`**
   - Docker, environment variables
   - Scripts, CI/CD
   - Networking, infrastructure

8. **`agents/briefs/QA.md`**
   - Unit tests, integration tests
   - Test fixtures, runbooks
   - Test automation

### Updated Files

9. **`CURSOR_INSTRUCTIONS.md`** (updated)
   - Added reference to `docs/WORKFLOW.md`
   - Added multi-agent workflow section

---

## 🔄 How It Works

### Flow Diagram

```
┌─────────────────┐
│  Orchestrator   │  (Composer 1)
│  (Sprint Plan)  │
└────────┬────────┘
         │
         ├───> Reads: docs/WORKFLOW.md, plans/task_plan.md
         │
         ├───> Generates: Sprint Plan + Agent Prompts
         │
         └───> Spawns Agents
                  │
                  ├───> Backend Agent (Composer 2)
                  │     └───> Reads: agents/briefs/BACKEND.md
                  │     └───> Invokes: @python-patterns, @api-patterns
                  │     └───> Edits: services/api/**, services/features/**
                  │
                  ├───> Data Agent (Composer 3)
                  │     └───> Reads: agents/briefs/DATA.md
                  │     └───> Invokes: @postgres-best-practices, @database-design
                  │     └───> Edits: services/data/models.py, alembic/**
                  │
                  ├───> DevOps Agent (Composer 4)
                  │     └───> Reads: agents/briefs/DEVOPS.md
                  │     └───> Edits: docker-compose.yml, .env.example
                  │
                  └───> QA Agent (Composer 5)
                        └───> Reads: agents/briefs/QA.md
                        └───> Invokes: @testing-patterns
                        └───> Edits: tests/**, docs/runbooks/**

         ┌───────────────┐
         │  Integrator   │  (Composer 1, after agents)
         │  (Merge Pass) │
         └───────────────┘
                  │
                  ├───> Resolves conflicts
                  ├───> Runs acceptance tests
                  ├───> Updates documentation
                  └───> Marks sprint complete
```

---

## 📖 Reading Order

### For Orchestrator (First Time)

1. `docs/WORKFLOW.md` - Understand the workflow
2. `docs/MULTI_AGENT_QUICKSTART.md` - Quick reference
3. `plans/task_plan.md` - Current sprint tasks
4. `agents/briefs/*.md` - All agent briefs

### For Each Agent

1. `docs/WORKFLOW.md` - Skill invocation rules
2. `agents/briefs/[YOUR_ROLE].md` - Your specific brief
3. Relevant skills from `agents/skills/skills/`
4. `docs/architecture.md` - System design
5. `docs/api-contracts.md` or `docs/data-contracts.md` - Contracts

---

## 🎯 Key Concepts

### 1. Skills-First Approach

**Rule:** Before any coding, invoke relevant skills.

```
Task → Check Skills → Invoke Skill → Follow Checklist → Code
```

**Skills Available:**
- `@using-superpowers` - Always first
- `@python-patterns` - Python code
- `@postgres-best-practices` - Database
- `@api-patterns` - FastAPI
- `@testing-patterns` - Tests
- `@clean-code` - Quality

### 2. File Ownership

**Strict boundaries prevent conflicts:**

- **Architect:** Docs only, no code
- **Backend:** `services/api/**`, `services/features/**`
- **Data:** `services/data/models.py`, `alembic/**`
- **DevOps:** `docker-compose.yml`, `.env.example`
- **QA:** `tests/**`, `docs/runbooks/**`

### 3. Output Contracts

**Each sprint has defined outputs:**

- **Sprint 1:** DB models, migrations, Docker setup
- **Sprint 2:** Feature pipeline, strategy framework
- **Sprint 3:** Backtesting engine, reports
- **Sprint 4:** API endpoints, dashboard
- **Sprint 5:** Execution, risk guardrails

### 4. Acceptance Criteria

**Each agent must provide:**

- Functional tests
- Technical validation
- Documentation updates
- Skill evidence (checklist completion)

---

## 🚀 Getting Started

### Option 1: Multi-Agent (Fast)

1. Open Composer 1 → Paste Orchestrator prompt
2. Copy agent prompts → Open Composer 2-6
3. Run in parallel → All agents work simultaneously
4. Integrator merges → Composer 1 final pass

**Time:** ~3-5x faster than sequential

### Option 2: Single Agent (Sequential)

1. Read `docs/WORKFLOW.md`
2. Read `agents/briefs/BACKEND.md` (or your role)
3. Follow skill invocation rules
4. Work through sprint tasks sequentially

**Time:** Slower but simpler

---

## 📚 Reference Documentation

### Must Read

- **`docs/WORKFLOW.md`** - Complete workflow protocol
- **`agents/briefs/[ROLE].md`** - Your agent brief
- **`plans/task_plan.md`** - Current sprint tasks

### Reference

- **`docs/architecture.md`** - System design
- **`docs/api-contracts.md`** - API specifications
- **`docs/data-contracts.md`** - Database schemas
- **`adr/*.md`** - Architectural decisions

### Skills

- **`agents/skills/skills/`** - Skills catalog
- **`agents/skills/skills/using-superpowers/SKILL.md`** - Skill usage rules

---

## ✅ Verification Checklist

**Before starting a sprint:**

- [ ] Read `docs/WORKFLOW.md`
- [ ] Read relevant agent briefs
- [ ] Understand file ownership boundaries
- [ ] Know which skills to invoke
- [ ] Have acceptance criteria defined

**After sprint completion:**

- [ ] All agents completed their tasks
- [ ] Acceptance tests passed
- [ ] Documentation updated
- [ ] `plans/task_plan.md` marked complete
- [ ] No file ownership violations

---

## 🎓 Learning Path

**New to multi-agent workflow?**

1. **Start:** Read `docs/MULTI_AGENT_QUICKSTART.md`
2. **Understand:** Read `docs/WORKFLOW.md`
3. **Practice:** Run Sprint 2 with multi-agent setup
4. **Master:** Run Sprint 3-5 with full parallelization

**Already familiar?**

1. Jump to `docs/WORKFLOW.md` → Agent Prompts section
2. Use Orchestrator prompt template
3. Copy agent prompts to separate Composer tabs
4. Run in parallel

---

## 🔧 Troubleshooting

### Agents editing wrong files

**Solution:** Re-read `agents/briefs/[ROLE].md` → File Ownership section

### Skills not being invoked

**Solution:** Re-read `docs/WORKFLOW.md` → Skill Invocation Rules

### Conflicts between agents

**Solution:** Check file ownership boundaries. Agents should not overlap.

### Tests failing after integration

**Solution:** Each agent should provide passing tests. Integrator runs final validation.

---

## 📞 Support

**Questions?**

1. Check `docs/WORKFLOW.md` - Most answers are there
2. Check `agents/briefs/[ROLE].md` - Role-specific guidance
3. Check `docs/MULTI_AGENT_QUICKSTART.md` - Quick reference

**Issues?**

- File ownership violation → Check briefs
- Skills not working → Check `@using-superpowers`
- Tests failing → Check QA agent brief

---

## 🎉 Success Metrics

**Multi-agent workflow is working when:**

- ✅ Multiple Composer tabs running simultaneously
- ✅ Each agent stays in their file boundaries
- ✅ Skills are invoked before coding
- ✅ Acceptance tests pass
- ✅ Documentation is updated
- ✅ Sprint completes faster than sequential

**Expected speedup:** 3-5x faster than sequential development.

---

**Last Updated:** 2026-01-26  
**Version:** 1.0
