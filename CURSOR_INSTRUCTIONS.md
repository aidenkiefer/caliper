# 🤖 Cursor Agent Instructions

## 🛑 STOP! READ THIS FIRST

You are about to begin the **Implementation Phase** of the Quant ML Trading Platform.
A comprehensive planning phase has already been completed by the **Planning Orchestrator (Antigravity)**. Your job is to **execute** this plan.

---

## 1. 🧠 Critical Context & Onboarding

Before writing a single line of code, you must upload the context of what we are building and *how* we build it.

### A. The "Why" and "What"
1.  **Read `docs/floorplan.md`**: This is the "God Class" document. It explains the end-to-end vision: a modular, risk-managed trading platform for stocks/options with a Next.js dashboard.
2.  **Read `docs/research.md`**: Understand the *financial logic*. This explains why we use specific ML models (XGBoost), why we care about "Risk Level 6", and the math behind our decisions.
3.  **Read `plans/findings.md`**: This summarizes the key research insights and design choices made during the planning phase.

### B. The "How" (Skills & Superpowers)
This project uses a **Skills-First** approach. You have a library of "Superpowers" in `.agents/skills`.
**You MUST read `.agents/skills/README.md`** to understand what tools are available to you.

**Key Skills to use during Implementation:**
*   `services/data` implementation? -> Use **@python-best-practices** (if available) or standard patterns.
*   `services/api` implementation? -> Use **@api-patterns** and **@fastapi-best-practices**.
*   `apps/dashboard` implementation? -> Use **@nextjs-best-practices`** and **@frontend-design**.
*   Database work? -> Use **@database-design**.

*Note: If you are using Cursor's `@Codebase` feature, these skills may be indexed. If not, manually read the relevant skill markdown file in `.agents/skills/` before starting a complex task.*

---

## 2. The Master Plan (Source of Truth)

The Planning Orchestrator has created a detailed roadmap for you.
**You are NOT starting from scratch.** You are picking up the baton.

*   **Project Schedule:** [plans/task_plan.md](plans/task_plan.md) - This is your Bible. **Follow the "Cursor Implementation Sprint" section exactly.**
*   **System Design:** [docs/architecture.md](docs/architecture.md) - The map of the territory.
*   **Database Schema:** [docs/data-contracts.md](docs/data-contracts.md) - **Strict Control.** Do not invent schemas. Use these exact SQL contracts.
*   **API Specs:** [docs/api-contracts.md](docs/api-contracts.md) - Your backend endpoints are already defined here.
*   **Security & Risk:** [docs/security.md](docs/security.md) & [docs/risk-policy.md](docs/risk-policy.md) - These are non-negotiable compliance rules.

---

## 3. Your Mission: execute the "Cursor Implementation Sprint"

Your goal is to build the platform in **5 Sprints** as defined in `plans/task_plan.md`.

**Sprint 1 (Immediate Focus):**
1.  **repo-setup**: Initialize the Monorepo (Git, Poetry, Node).
2.  **infra-setup**: Create `docker-compose.yml` with Postgres (TimescaleDB) & Redis.
3.  **db-migrations**: Apply the schemas from `data-contracts.md` using Alembic.
4.  **data-ingestion**: Build the `AlpacaProvider` in `services/data`.

### Rules of Engagement

1.  **Do Not Guess:** If a schema or contract is defined in `/docs`, use it exactly. Do not improvise new field names.
2.  **Step-by-Step:** Do not try to build the whole system at once. Work Sprint by Sprint.
3.  **Update Progress:** Check off items in `plans/task_plan.md` as you complete them.
4.  **ADR Compliance:** Read the `/adr` folder. We use a Monorepo, FastAPI, and TimescaleDB. Do not deviate from these decisions.

---

## 4. How to Start

Run this command to acknowledge you represent the Implementation Team:
`echo "Cursor Agent: Context loaded. Starting Sprint 1..."`

Then:
1.  Open `plans/task_plan.md`.
2.  Read the **Sprint 1** checklist.
3.  Begin with Item 1: **Repo Setup**.
