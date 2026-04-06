# Ticket: 12-07-session-integration

## Task
Wire `FeatureBuilder` into `services/polymarket/session.py` and update `PolymarketMMStrategy.on_market_data` to optionally accept a `FeatureSnapshot` in addition to (or instead of) raw `OrderbookState`.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Modify: `services/polymarket/session.py`
- Modify: `services/polymarket/strategy.py` (update `on_market_data` signature)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-12-feature-layer-spec.md` (section: Integration with PolymarketMMStrategy)

### Optional read-only references
- `services/features/polymarket/builder.py` (FeatureBuilder interface — read-only)
- `services/features/polymarket/store.py` (FeatureStore interface — read-only)
- `packages/common/polymarket_schemas.py` (FeatureSnapshot — read-only)

### Example files (read-only, optional)
- `services/polymarket/session.py` (current session orchestrator — read before modifying)
- `services/polymarket/strategy.py` (current strategy — read before modifying)

## Agent type
backend-agent

## Skill pack
- `async-python-patterns` (asyncio task wiring, queue consumer)

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 4
- Max total tool calls: 11

## Done criteria

**`services/polymarket/session.py`:**
- Instantiates `CLOBSource`, `BinanceSource`, and `FeatureBuilder` during session startup (after existing market discovery)
- Starts `FeatureBuilder` as a background task alongside the existing heartbeat and quoting tasks
- Launches a `_feature_consumer` coroutine that:
  1. Reads from `FeatureBuilder.output_queue` (blocking `await queue.get()`)
  2. Calls `FeatureStore.write(snapshot)` (fire-and-forget with logged exception on failure — never blocks the quoting loop)
  3. Calls `strategy.on_market_data(snapshot)` if the strategy accepts `FeatureSnapshot`
- On session shutdown, calls `FeatureBuilder.stop()` and `FeatureStore.close()`
- `FeatureStore` and `FeatureBuilder` are optional: if DB_URL is not configured, feature persistence is skipped (logged as WARNING) but builder still runs for strategy use

**`services/polymarket/strategy.py`:**
- `on_market_data` signature updated to accept `Union[OrderbookState, FeatureSnapshot]` (backward-compatible)
- If a `FeatureSnapshot` is passed: uses `snapshot.implied_probability`, `snapshot.spread`, `snapshot.near_close_flag`, and `snapshot.liquidity_score` to gate quoting decisions
- If an `OrderbookState` is passed (legacy): behavior unchanged (existing raw-orderbook path)
- No changes to the risk pipeline or order execution path

**`docs/plans/PROGRESS.md`** updated
