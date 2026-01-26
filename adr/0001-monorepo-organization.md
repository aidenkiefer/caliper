# 1. Monorepo Organization

date: 2026-01-25
status: accepted

## Context
We are building a quantitative trading platform composed of multiple distinct components:
- Python sub-services (Data, Features, Execution, Risk)
- TypeScript Frontend (Next.js Dashboard)
- Shared libraries (Strategy definitions, Schema contracts)

We need to decide how to organize the codebase. Deployment is targeted for a personal/small-team environment initially (VM + Vercel).

## Decision
We will use a **Monorepo** structure.

**Structure:**
- `/apps/dashboard` (Next.js)
- `/services/*` (Python micro-services)
- `/packages/*` (Shared Python/JS libs)
- `/docs` (Shared documentation)

## Consequences
### Positive
- **Atomic Commits:** Can update a Shared Schema and the Service that uses it in one commit.
- **Single Source of Truth:** `data-contracts` and `api-contracts` live alongside code.
- **Simplified DevEx:** One repo to clone. `docker-compose` at root spins up everything.

### Negative
- **CI Complexity:** Requires smart CI (e.g., Turborepo or specific GitHub Actions paths) to avoid rebuilding everything on every change.
- **Tooling Mixed:** Python (Poetry) and Node (npm/pnpm) tooling must coexist in root.

## Alternatives Considered
- **Polyrepo:** Separate repos for API, Dashboard, and Strategies. Rejected due to overhead of managing shared schema changes and syncing versions across 8+ repos for a single developer.
