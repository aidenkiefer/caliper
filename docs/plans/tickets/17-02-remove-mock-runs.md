# Ticket 17-02 — Remove mock runs (no dummy data)

## Goal

Stop serving hardcoded run/backtest data from the API. Until runs are persisted and wired to the real backtest/job system, the API should return:

- empty lists for `GET /v1/runs`
- 404 for unknown `GET /v1/runs/{id}`
- 501 for `POST /v1/runs` (not yet wired)

## Allowed files

- `services/api/routers/runs.py`
- `docs/ui-data-audit.md`

## Acceptance criteria

- No hardcoded/mock run objects are returned by the API.
- UI audit doc reflects that runs are not yet wired (and no longer mock-backed).

