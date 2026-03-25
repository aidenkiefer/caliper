# Caliper (quant) — Project memory

**Mission:** Caliper is a quantitative ML trading platform for stocks (options-ready) focused on learning and correctness, with strict risk management and human-in-the-loop safeguards. Paper trading comes first, with controlled promotion to live trading behind explicit controls.

## How to work

- **Bounded runs:** Every task is a ticket (`docs/workflow/ticket-template.md`). Edit only Allowed Files listed in the ticket.
- **Targeted reads:** Max 8 file reads, 6 grep/glob, 12 tool calls per ticket. Stop and ask before exceeding.
- **No verification runs:** Do not run build, dev, test, or compile to verify or confirm changes.
- **Specs once:** Read spec once per session → produce a Spec Summary (10–20 lines) → run tickets from the summary.
- **Lazy-load skills:** Ticket names the skill pack (0–2 core, 0–2 domain). Do not load the full skill registry.

## Hard constraints

- Always route order creation through risk controls (`services/risk`) — do not bypass kill switch / circuit breaker checks.
- Paper trading first; do not make changes that imply live trading or real-money execution without explicit instruction.
- Do not introduce new services based only on docs (e.g. don’t assume `services/data` exists) — implement only what exists under `services/` and `packages/` unless the ticket explicitly adds it.
- Never commit real secrets (API keys, broker credentials). Use `configs/environments/.env.example` patterns only.
- Edit only files in the Allowed Files list. Stop and ask if you need an unlisted file.

## Project map

- **Docs index:** `docs/INDEX.md` — primary doc map for agents and humans
- **Workflow:** `docs/workflow/` — execution-rules, ticket-template, skill-map, task-type-reference-map
- **Specs:** `docs/plans/specs/` (read-only; summarize once per session)
- **Tickets:** `docs/plans/tickets/` (one bounded task per run)
- **Progress:** `docs/plans/PROGRESS.md`
- **Historical progress:** `plans/progress.md`
- **Architecture:** `docs/architecture.md`
- **API contracts:** `docs/api-contracts.md`
- **Data contracts:** `docs/data-contracts.md`
- **Risk policy:** `docs/risk-policy.md`
- **Security:** `docs/security.md`
- **Design guide:** `docs/design-guidelines.md`
- **Runbooks:** `docs/runbooks/`
- **Dashboard:** `apps/dashboard/`
