# Ticket 17-05 — Dashboard: ranking/fleet wiring (no dummy data)

## Goal

Align the dashboard to the post-wiring behavior of ranking/fleet endpoints:

- `/v1/ranking/current` returns 503 until a durable source exists.
- `/v1/fleet/status` and `/v1/fleet/signals` return 503 until orchestrator snapshots/signals are persisted.
- `/v1/fleet/paper-trades` is DB-backed and returns raw trade fields from `pm.paper_trades` (no fabricated P&L).

## Allowed files

- `apps/dashboard/src/lib/types/models.ts`
- `apps/dashboard/src/lib/api.ts`
- `apps/dashboard/src/lib/hooks/use-fleet.ts`
- `apps/dashboard/src/lib/hooks/use-ranking.ts`
- `apps/dashboard/src/app/(dashboard)/platform/ranking-fleet/page.tsx`

## Acceptance criteria

- Dashboard compiles with the new `/fleet/paper-trades` response shape.
- Explorer page error messages are accurate (503 = not wired/persisted yet, not “needs DB_URL”).
- No UI path displays fake fleet/ranker data when demo mode is off.

