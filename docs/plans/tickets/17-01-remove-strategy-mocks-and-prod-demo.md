# Ticket 17-01 — Remove strategy mocks + prevent prod demo data

## Goal

Eliminate “dummy”/mock strategy data from the dashboard and API by:

1) Preventing `NEXT_PUBLIC_DEMO_MODE` from ever enabling demo fallbacks in **production** builds.
2) Replacing the FastAPI `/v1/strategies` list/detail endpoints (currently in-memory mocks) with responses derived from **real runtime paper data** (allocations/fills/snapshots).

## Scope / Non-goals

- Do **not** implement new trading logic.
- Do **not** build full strategy CRUD persistence yet.
- Prefer returning `—` / `null` for unknown metrics over fake zeros.

## Allowed files

- `apps/dashboard/src/lib/demo.ts`
- `apps/dashboard/src/lib/hooks/use-strategies.ts`
- `apps/dashboard/src/app/(dashboard)/strategies/page.tsx`
- `apps/dashboard/src/app/(dashboard)/strategies/[id]/page.tsx`
- `services/api/routers/strategies.py`
- `docs/ui-data-audit.md`

## Acceptance criteria

- In production builds, demo mode cannot be enabled via env vars.
- `GET /v1/strategies` and `GET /v1/strategies/{id}` no longer return hardcoded mock strategies.
- Dashboard no longer displays fake strategy metrics (shows `—` when unavailable).

