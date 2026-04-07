# Ticket 17-04 — Wire ranking + fleet HTTP endpoints (no mock data)

## Goal

Replace the mock-backed HTTP responses for:

- `GET /v1/ranking/current`
- `GET /v1/fleet/status`
- `GET /v1/fleet/signals`
- `GET /v1/fleet/paper-trades`

so that the API returns **real data** sourced from:

- DB tables (especially `pm.paper_trades`)
- runtime ranking logic where available

If an endpoint cannot be truthfully implemented yet (no durable source exists), it must return:

- a **503** (service unavailable) or **501** (not implemented), rather than fabricated mock payloads.

## Allowed files

- `services/api/routers/ranking.py`
- `services/api/routers/fleet.py`
- `services/fleet/paper_store.py`
- `services/fleet/schemas.py`
- `services/ranking/ranker.py`
- `services/ranking/schemas.py`
- `docs/ui-data-audit.md`

## Acceptance criteria

- No `_mock_*` helpers are used by the ranking/fleet HTTP routes.
- `GET /v1/fleet/paper-trades` returns real trades from `pm.paper_trades` when DB is configured.
- Other endpoints return real data if available; otherwise return 503/501 (no dummy data).

