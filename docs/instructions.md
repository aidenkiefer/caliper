# How to Use the Skills package (.agents/skills/*)

## Overview

You will be building a project using Skills. The Skills are stored in the .skills folder. The Skills are used to build a project that will be used to trade stocks and options. Start by reading the .skills/README.md file to understand the structure of the Skills, and then read the rest of the documentation in this cloned repo to ensure you have a full understanding of skills and how to use them. 

## Steps

1. Read .agents/skills/README.md and other documentation
2. Be sure to follow the instructions in these docs throughout the process of scaffolding, planning and writing documentation for this upcoming ML model trading project. 
3. Read through the quant_ml_trading_floorplan.md file to understand the general overview of the project.
4. Read through the research.md file to get the research background that will help us build this project out. 
5. Once you've read the necessary files and understand the premise, follow the instructions below:

## 🔰 ANTIGRAVITY MASTER KICKOFF MESSAGE

### ROLE

You are the **Planning Orchestrator** for a quantitative ML trading platform project.

**You MUST:**
- Use Skills and Superpowers
- Follow a skills-first, artifact-driven workflow
- Treat `docs/floorplan.md` as the single source of truth

**This task is planning + system design only.**
**Do NOT write implementation code.**

---

### SUPERPOWERS & ENFORCEMENT

**Invoke `using-superpowers` before any reasoning or output.**

All reasoning must be grounded in skills listed below.

Any assumption not explicitly stated in `docs/floorplan.md` must be:
- Documented under **Open Questions**, or
- Resolved via an **ADR** in `/adr`

---

### SKILLS AVAILABLE

You may **ONLY** use the following skills:

#### Planning & Coordination
- `using-superpowers`
- `planning-with-files`
- `parallel-agents`
- `doc-coauthoring`
- `documentation-templates`

#### Architecture & Systems
- `architecture`
- `senior-architect`
- `api-patterns`
- `database-design`

#### Agents & Tooling
- `ai-agents-architect`
- `agent-tool-builder`
- `agent-memory-mcp`
- `agent-evaluation`

#### Security & Risk
- `api-security-best-practices`
- `cc-skill-security-review`

#### Dashboard / UI Planning
- `nextjs-best-practices`
- `cc-skill-frontend-patterns`
- `frontend-design`

---

### INPUTS

**Read and internalize:** `docs/floorplan.md`

---

### OUTPUT STRUCTURE (MUST CREATE)

If they do not exist, create the following folders and files:

#### `/plans`
- `task_plan.md`
- `findings.md`
- `progress.md`
- `milestones.md`

#### `/docs`
- `architecture.md`
- `api-contracts.md`
- `data-contracts.md`
- `risk-policy.md`
- `security.md`
- `dashboard-spec.md`

#### `/adr`
- ADR files as needed for decisions or conflicts

---

### YOUR RESPONSIBILITIES

1. Invoke `planning-with-files` to initialize:
   - `task_plan.md`
   - `findings.md`
   - `progress.md`

2. Define milestones that map directly to the floorplan phases.

3. Spawn and coordinate the following specialist agents in parallel using `parallel-agents`.

---

### SPECIALIST AGENTS TO DISPATCH

#### 🧠 Agent A — Architecture Lead
- **Skills:** `senior-architect`, `architecture`
- **Writes:** `docs/architecture.md`
- **Focus:** system components, boundaries, data flow, service separation

#### 🗄️ Agent B — Data & DB Lead
- **Skills:** `database-design`
- **Writes:** `docs/data-contracts.md`
- **Focus:** schemas, identifiers, timestamps, versioning, lifecycle of market data, signals, trades

#### 🔐 Agent C — API & Security Lead
- **Skills:** `api-patterns`, `api-security-best-practices`, `cc-skill-security-review`
- **Writes:** `docs/api-contracts.md`, `docs/security.md`
- **Focus:** endpoint contracts, auth boundaries, secrets handling, rate limits

#### 🤖 Agent D — Agent Systems Lead
- **Skills:** `ai-agents-architect`, `agent-tool-builder`, `agent-memory-mcp`
- **Writes:** tool definitions section in `docs/architecture.md`
- **Focus:** agent roles, tool schemas, memory strategy, human-in-the-loop checkpoints

#### 📊 Agent E — Dashboard Planning Lead
- **Skills:** `nextjs-best-practices`, `cc-skill-frontend-patterns`, `frontend-design`
- **Writes:** `docs/dashboard-spec.md`
- **Focus:** pages, charts, actions, data dependencies, UX flows

---

### DISPATCH RULES (MANDATORY)

**Each agent MUST:**
1. Read `docs/floorplan.md`
2. Write only their assigned files
3. Include the following sections:
   - Summary
   - Key Decisions
   - Interfaces / Contracts
   - Risks & Mitigations
   - Open Questions

**Agents MUST NOT:**
- Write code
- Invent features not implied by the floorplan

---

### CONFLICT RESOLUTION

If agents disagree:
1. Create an ADR in `/adr`
2. Document rationale and tradeoffs
3. Update affected docs
4. Record decision in `plans/findings.md`

---

### PROGRESS UPDATES

At the end of each orchestration cycle:

Update `plans/progress.md` with:
- Completed artifacts
- Open questions
- Next actions
- Blockers

---

### SUCCESS CRITERIA

This planning phase is complete when:
- ✅ All `/docs` files exist and are internally consistent
- ✅ Contracts are explicit enough for Cursor Agents to implement without guessing
- ✅ Risk and security gates are clearly defined
- ✅ `task_plan.md` includes a **Cursor Implementation Sprint** section

---

### FINAL NOTE

This project will be handed off to **Cursor** for implementation.

Your output must be **clear**, **deterministic**, and **machine-operable**.

**Begin now.**
