# Ticket 17-03 — Health endpoints: remove mock signals

## Goal

Stop returning “healthy” mock values from `/v1/health` when the system has not been wired to real checks.

Minimum:
- **Database**: real connectivity + latency check (`SELECT 1`).
- Other services: report `degraded`/`unknown` style status rather than fabricated healthy values.

## Allowed files

- `services/api/routers/health.py`
- `docs/ui-data-audit.md`

## Acceptance criteria

- `/v1/health` database status reflects real DB connectivity.
- No other service is reported as healthy unless it is actually checked.

