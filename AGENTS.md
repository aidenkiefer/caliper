# Caliper (quant)

Quantitative ML trading platform with backtesting, risk management, and a Next.js dashboard — focused on learning, correctness, and safety (paper trading first).

## How to work

- **Bounded runs:** Every task is a ticket. Edit only Allowed Files listed in the ticket.
- **Targeted reads:** Max 8 file reads, 6 grep/glob, 12 tool calls per ticket. Stop and ask if you need more.
- **No verification runs:** Do not run build, dev, test, or compile to confirm changes.
- **Specs once:** Read spec once per session → Spec Summary → run tickets from summary.
- **Lazy-load skills:** Ticket names the skill pack. Do not load the full skill registry.

## Hard constraints

- Always route order creation through risk controls; do not bypass kill switch / circuit breaker checks.
- Paper trading first; do not imply live trading unless explicitly requested.
- Never commit secrets; use `.env.example` patterns only.

## Where to look

- **Docs index:** `docs/INDEX.md`
- **Workflow:** `docs/workflow/workflow.md`
- **Specs:** `docs/plans/specs/`
- **Tickets:** `docs/plans/tickets/`
- **Progress:** `docs/plans/PROGRESS.md`
- **Historical progress:** `plans/progress.md`
- **Architecture:** `docs/architecture.md`
- **API contracts:** `docs/api-contracts.md`
- **Data contracts:** `docs/data-contracts.md`
- **Risk policy:** `docs/risk-policy.md`
