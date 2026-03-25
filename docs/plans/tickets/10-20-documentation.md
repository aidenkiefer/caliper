# Ticket: 10-20-documentation

## Task
Write user documentation for Polymarket service: setup guide, configuration reference, and operational runbook.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/docs/SETUP.md`
- Create: `services/polymarket/docs/CONFIG.md`
- Create: `services/polymarket/docs/RUNBOOK.md`
- Modify: `services/polymarket/README.md` (add links to docs)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (all sections)

### Optional read-only references
- `docs/runbooks/` (example runbook patterns)

## Agent type
docs-agent

## Skill pack
None required (documentation task)

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 2
- Max total tool calls: 10

## Done criteria
- `SETUP.md` covers:
  - Prerequisites (Polymarket account, Polygon wallet, USDC, MATIC)
  - Environment variable setup (`.env.polymarket` template)
  - Database migration (`alembic upgrade head`)
  - Dependency installation (`poetry install`)
  - Test run (`polymarket-session --dry-run`)
- `CONFIG.md` documents all `PolymarketConfig` fields with types, defaults, and examples
- `RUNBOOK.md` covers:
  - Starting a session (`polymarket-session`)
  - Monitoring (logs, DB queries)
  - Emergency shutdown (manual cancel-all, kill switch)
  - Post-session analysis (SQL queries for PnL, adverse selection, regime performance)
  - Common errors and troubleshooting
- `README.md` updated with links to all docs
- `docs/plans/PROGRESS.md` updated
