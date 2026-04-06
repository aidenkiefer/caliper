# Ticket: 12-09-unit-tests

## Task
Write unit tests covering every feature formula across all 4 feature families, Pydantic schema validation, `FeatureStore` read/write, and regime label discretization with minimum-hold filter logic.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `tests/unit/features/test_feature_builder_formulas.py`
- Create: `tests/unit/features/test_feature_schemas.py`
- Create: `tests/unit/features/test_feature_store.py`
- Create: `tests/unit/features/test_regime_labels.py`
- Create: `tests/unit/features/__init__.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-12-feature-layer-spec.md` (Feature Families tables, AC-4, AC-7)

### Optional read-only references
- `services/features/polymarket/builder.py` (formulas to test — read-only)
- `packages/common/polymarket_schemas.py` (FeatureSnapshot — read-only)
- `services/features/polymarket/store.py` (FeatureStore interface — read-only)
- `tests/unit/` (existing test patterns and fixtures)

## Agent type
backend-agent

## Skill pack
None required (pytest unit tests)

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 3
- Max total tool calls: 11

## Done criteria

**`test_feature_builder_formulas.py`** — formula unit tests:

*Family 1 — Market State:*
- `test_mid_price`: input `best_bid=0.48, best_ask=0.52` → `mid_price == Decimal("0.50")`
- `test_implied_probability_tight_spread`: spread ≤ 0.10 → equals midpoint
- `test_implied_probability_wide_spread`: spread > 0.10 → equals `last_trade_price`
- `test_spread_bps`: explicit numeric assertion (e.g., spread=0.02, mid=0.50 → spread_bps=400)
- `test_book_depth_bid_5tick`: sum of sizes on bid levels within 5 ticks of best bid

*Family 2 — Microstructure:*
- `test_order_book_imbalance_balanced`: equal depths → imbalance == 0
- `test_order_book_imbalance_bid_heavy`: more bid depth → positive imbalance
- `test_trade_flow_imbalance_1m`: rolling buy/sell volumes → correct difference
- `test_vpin_proxy`: buy_vol=800, sell_vol=200, total=1000 → vpin=0.6
- `test_last_5min_volume_share`: fraction calculation with explicit values

*Family 3 — Probabilistic:*
- `test_btc_distance_to_open`: `ln(51000 / 50000)` ≈ 0.01980; asserts within 1e-5
- `test_btc_rv_1m`: 3 log-returns provided → correct sum of squares
- `test_btc_momentum_5m`: log return over 5 minutes with 5 klines
- `test_btc_sign_persistence_5m`: 4 of 5 returns positive → persistence == 0.8

*Family 4 — Regime formulas:*
- `test_liquidity_score_positive`: depth > 0, spread > 0 → score > 0
- `test_competitive_pressure`: narrow spread → higher pressure than wide spread
- `test_near_close_flag_true`: `time_to_close_seconds=300` → `near_close_flag == True`
- `test_near_close_flag_false`: `time_to_close_seconds=1500` → `near_close_flag == False`

**`test_regime_labels.py`** — AC-4 compliance:
- `test_vol_regime_classification`: low/medium/high with explicit RV values crossing thresholds
- `test_trend_regime_classification`: trending / mean_reverting / neutral with sign persistence values
- `test_toxicity_regime_classification`: low/medium/high VPIN values
- `test_spread_regime_classification`: tight / normal / wide vs rolling median
- `test_time_bucket_early_mid_late`: 10min → "early", 30min → "mid", 55min → "late"
- `test_regime_minimum_hold_filter`: label does NOT flip after 1 or 2 ticks in new regime; flips only after 3 consecutive ticks

**`test_feature_schemas.py`** — schema validation:
- `test_feature_snapshot_valid`: full valid dict → `FeatureSnapshot` constructs without error
- `test_feature_snapshot_missing_required_field`: missing `market_id` → `ValidationError`
- `test_feature_snapshot_invalid_regime_literal`: `vol_regime="extreme"` → `ValidationError`
- `test_data_staleness_flag_default_false`: newly constructed snapshot → `data_staleness_flag == False`

**`test_feature_store.py`** — storage (uses in-memory mocks, no real DB):
- `test_write_calls_insert`: `FeatureStore.write(snapshot)` calls asyncpg with correct SQL pattern
- `test_read_latest_returns_none_empty`: mock returns no rows → `read_latest` returns `None`
- `test_read_latest_deserializes`: mock returns JSONB dict → `read_latest` returns valid `FeatureSnapshot`
- `test_read_window_empty`: no rows → returns `[]`
- `test_not_connected_raises`: calling `write()` before `connect()` raises `RuntimeError`

All test functions use explicit numeric assertions (no `assert result is not None` without value check). Tests are deterministic and do not make real network calls.

**`docs/plans/PROGRESS.md`** updated
