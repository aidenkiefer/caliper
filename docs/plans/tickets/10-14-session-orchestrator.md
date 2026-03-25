# Ticket: 10-14-session-orchestrator

## Task
Implement the session orchestrator that coordinates all components for a single trading session.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/session.py`
- Create: `tests/integration/polymarket/test_session.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 2.2)

### Optional read-only references
- All component modules: `market_discovery.py`, `data_feed.py`, `quoting_engine.py`, `executor.py`, `safety.py`, `recorder.py`, `wallet.py`

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 12
- Max grep/glob operations: 5
- Max total tool calls: 25

## Done criteria
- `session.py` implements `SessionOrchestrator` class with methods:
  - `async def run_session(config: PolymarketConfig) -> None`
- Execution flow (from spec section 2.2):
  1. Market discovery
  2. Wallet balance check and initial USDC split
  3. Session record creation
  4. Data feed start (WebSocket + Binance poll)
  5. Heartbeat start
  6. Main loop: requote every `requote_interval_seconds` until wind-down
  7. Wind-down: cancel all, stop heartbeat, stop data feed
  8. Post-session: compute toxic flow, finalize session record
- Handles errors gracefully: emergency shutdown on critical failures, retry on transient errors
- Integration tests use mocked API clients and DB, cover: full session flow, wind-down timing, emergency shutdown
- `docs/plans/PROGRESS.md` updated
