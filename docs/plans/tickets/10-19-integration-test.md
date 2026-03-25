# Ticket: 10-19-integration-test

## Task
Create end-to-end integration test for a full Polymarket trading session using mocked APIs.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `tests/integration/polymarket/test_full_session.py`
- Create: `tests/integration/polymarket/fixtures.py` (mock API responses)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 2.2)

### Optional read-only references
- `services/polymarket/session.py`
- `tests/fixtures/` (example fixture patterns)

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 10
- Max grep/glob operations: 5
- Max total tool calls: 20

## Done criteria
- `test_full_session.py` implements `test_full_session_flow()` that:
  1. Mocks Gamma API (returns test market)
  2. Mocks CLOB API (order placement, cancellation, heartbeat, WebSocket)
  3. Mocks Binance API (returns test candle)
  4. Mocks wallet operations (balance, split, sign)
  5. Uses in-memory SQLite for database
  6. Runs `SessionOrchestrator.run_session(config)` with short duration (30s)
  7. Asserts: session created, orders placed, fills recorded, snapshots written, session finalized
- `fixtures.py` provides reusable mock responses for all APIs
- Test covers: normal flow, wind-down, emergency shutdown scenario
- Test runs in <5 seconds
- `docs/plans/PROGRESS.md` updated
