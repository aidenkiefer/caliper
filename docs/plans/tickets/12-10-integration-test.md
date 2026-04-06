# Ticket: 12-10-integration-test

## Task
Write an integration test that starts `FeatureBuilder` against mock `CLOBSource` and `BinanceSource` implementations, verifies 3 consecutive `FeatureSnapshot` objects are produced and written to a mock `FeatureStore`, and confirms determinism (AC-5: same inputs → identical output).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `tests/integration/features/test_feature_pipeline_integration.py`
- Create: `tests/integration/features/__init__.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-12-feature-layer-spec.md` (sections: AC-5, AC-7 — integration test requirement)

### Optional read-only references
- `services/features/polymarket/builder.py` (FeatureBuilder interface — read-only)
- `services/features/polymarket/store.py` (FeatureStore interface — read-only)
- `services/features/polymarket/sources/clob.py` (CLOBSource interface — read-only)
- `services/features/polymarket/sources/binance.py` (BinanceSource interface — read-only)
- `tests/integration/` (existing integration test patterns)

## Agent type
backend-agent

## Skill pack
- `async-python-patterns` (asyncio test patterns, pytest-asyncio)

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 3
- Max total tool calls: 10

## Done criteria

**`test_feature_pipeline_integration.py`:**

*Mock implementations:*
- `MockCLOBSource`: in-test stub implementing the `CLOBSource` interface
  - `get_orderbook_state()` returns a fixed `OrderbookState` (best_bid=0.48, best_ask=0.52, depths, timestamps)
  - `fetch_fee_rate()` returns `Decimal("0.0025")`
  - `fetch_reward_config()` returns `RewardConfig(eligible=True, max_spread=Decimal("0.03"), min_size=Decimal("5"))`
  - `source_timestamp` set to `datetime.utcnow()`
- `MockBinanceSource`: in-test stub implementing the `BinanceSource` interface
  - `get_btc_price()` returns `Decimal("50100")`
  - `get_hour_open()` returns `Decimal("50000")`
  - `get_kline_buffer()` returns 15 fixed `KlineBar` objects with predictable prices
  - `get_premium_index()` returns fixed `PremiumIndex(funding_rate=0.0001, mark_price=50105, index_price=50100)`
  - `source_timestamp` set to `datetime.utcnow()`

*Test: 3 consecutive snapshots produced (AC-7):*
```
@pytest.mark.asyncio
async def test_three_consecutive_snapshots_written():
```
- Creates `FeatureBuilder(clob=MockCLOBSource(), binance=MockBinanceSource(), tick_seconds=0.05)`
- Creates `MockFeatureStore` (in-memory list that appends on `write()`)
- Starts builder, waits 0.5 seconds (enough for 3+ ticks at 50ms cadence), stops builder
- Asserts `len(mock_store.snapshots) >= 3`
- Asserts each snapshot is a valid `FeatureSnapshot` (Pydantic validates on construction)
- Asserts `snapshot.market_id` is set correctly

*Test: determinism (AC-5):*
```
async def test_deterministic_output():
```
- Constructs `FeatureBuilder` with identical mock sources twice (same fixed inputs)
- Calls `_compute_snapshot()` directly (bypassing tick loop) from both instances
- Asserts both snapshots are equal (`snapshot1 == snapshot2`) for all numeric fields
- Asserts no non-deterministic fields (e.g., no random state, no `datetime.now()` side effects in formulas)

*Test: staleness flag set when source is stale:*
```
async def test_staleness_flag_set():
```
- `MockCLOBSource.source_timestamp` set to `datetime.utcnow() - timedelta(seconds=45)` (> 30s threshold)
- Calls `_compute_snapshot()`
- Asserts `snapshot.data_staleness_flag == True`

*Test: staleness flag clear when sources are fresh:*
- Both sources have recent timestamps → `data_staleness_flag == False`

All tests use `@pytest.mark.asyncio`. No real network calls. Tests complete in < 2 seconds.

**`docs/plans/PROGRESS.md`** updated with Sprint 12 ticket completion note (all 10 tickets generated)
