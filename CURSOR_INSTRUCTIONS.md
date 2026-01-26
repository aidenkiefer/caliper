# 🤖 Cursor Agent Instructions

## 🛑 STOP! READ THIS FIRST

You are about to begin the **Implementation Phase** of the Quant ML Trading Platform.
A comprehensive planning phase has already been completed. Your job is to **execute** the plan, not reinvent it.

### 1. Context & Source of Truth

*   **Master Plan:** [plans/task_plan.md](plans/task_plan.md) - This is your project schedule. **Follow the "Cursor Implementation Sprint" section exactly.**
*   **Architecture:** [docs/architecture.md](docs/architecture.md) - Use this for system boundaries and service design.
*   **Database:** [docs/data-contracts.md](docs/data-contracts.md) - **Strictly follow** these SQL schemas and Pydantic models.
*   **API:** [docs/api-contracts.md](docs/api-contracts.md) - Implement these endpoints exactly as defined.
*   **Rules:** [docs/risk-policy.md](docs/risk-policy.md) and [docs/security.md](docs/security.md) must be enforced in code.

### 2. Your Mission

Your goal is to build the platform in **5 Sprints** as defined in `plans/task_plan.md`.

**Sprint 1 (Immediate Focus):**
1.  Initialize Monorepo (Git, Poetry, Node).
2.  Setup `docker-compose` with Postgres (TimescaleDB) & Redis.
3.  Implement `services/data` and the `AlpacaProvider`.

### 3. Rules of Engagement

1.  **Do Not Guess:** If a schema or contract is defined in `/docs`, use it exactly. Do not improvise new field names.
2.  **Step-by-Step:** Do not try to build the whole system at once. Work Sprint by Sprint.
3.  **Update Progress:** Check off items in `plans/task_plan.md` as you complete them.
4.  **Ask Questions:** If you find a conflict between documents, ask the user for clarification before writing code.

### 4. How to Start

Run this command to acknowledge you understand the plan:
`echo "Cursor Agent starting Sprint 1..."`

Then, open `plans/task_plan.md`, read the "Sprint 1" checklist, and begin.
