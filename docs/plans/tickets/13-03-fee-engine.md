# Ticket 13-03: Fee Engine + Unit Tests

## Task

Implement `FeeEngine` with the exact Polymarket fee formula, both pre/post March-30-2026 fee regimes, maker rebate estimation, and liquidity reward credit calculation. Include unit tests validating numeric accuracy per AC-3.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/simulation/execution/fee_engine.py`
- Create: `tests/unit/simulation/test_fee_engine.py`
- Modify: `services/simulation/execution/__init__.py` (exports)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ FeeEngine)
- `services/simulation/schemas.py` (SimFill, PnLComponents)

## Done criteria

### `services/simulation/execution/fee_engine.py`

**`FeeRegime`** (dataclass):
```python
@dataclass
class FeeRegime:
    fee_rate: Decimal
    exponent: int          # 2 for pre-Mar30, 1 for post-Mar30
    maker_rebate_pct: Decimal

    @classmethod
    def pre_mar30_crypto(cls) -> "FeeRegime":
        return cls(fee_rate=Decimal("0.25"), exponent=2, maker_rebate_pct=Decimal("0.20"))

    @classmethod
    def post_mar30_crypto(cls) -> "FeeRegime":
        return cls(fee_rate=Decimal("0.072"), exponent=1, maker_rebate_pct=Decimal("0.20"))

    @classmethod
    def for_date(cls, market_created_at: datetime, current_date: date) -> "FeeRegime":
        # Returns post_mar30_crypto if both market was created on/after 2026-03-30
        # AND current_date >= 2026-03-30; otherwise pre_mar30_crypto.
        # (Markets created before Mar-30 retain pre-Mar-30 rates even after Mar-30)
        ...
```

**`FeeEngine`**:
- `__init__(regime: FeeRegime, lr_pool_per_hour: Decimal = Decimal("50"))`
- `taker_fee(shares: Decimal, price: Decimal) -> Decimal`:
  ```
  fee = shares * price * regime.fee_rate * (price * (1 - price)) ** regime.exponent
  ```
  Result always >= 0. Use `Decimal` arithmetic throughout.
- `maker_rebate_estimate(fill: SimFill, total_fee_equivalent_in_market: Decimal) -> Decimal`:
  ```
  your_fee_eq = fill.fill_size * fill.fill_price * regime.fee_rate * (fill.fill_price * (1 - fill.fill_price)) ** regime.exponent
  rebate = (your_fee_eq / total_fee_equivalent_in_market) * rebate_pool
  ```
  Sets `fill.rebate_estimated = True`. Returns 0 if `total_fee_equivalent_in_market` is 0.
- `liquidity_reward_credit(bid_size: Decimal, ask_size: Decimal, spread: Decimal, max_spread: Decimal, min_size: Decimal) -> Decimal`:
  ```
  quote_score = min(bid_size, ask_size) * max(0, 1 - spread / max_spread)
  ```
  Returns `quote_score` (caller applies hourly pooling). Returns 0 if `bid_size` or `ask_size` is 0, or if `spread >= max_spread`.
- `compute_pnl_components(fills: List[SimFill], mark_prices: List[Decimal]) -> PnLComponents`:
  Computes full PnL attribution. `spread_capture` = sum of `(fill_price - mid_at_fill) * fill_size * (1 if BUY else -1)`. `inventory_drift` from mark-to-market changes between fills. `taker_fee` = negative sum of taker fees. `maker_rebate` = estimated rebate sum (flagged as estimate). Returns `PnLComponents`.

### `tests/unit/simulation/test_fee_engine.py`

**Regime selection:**
- `test_for_date_pre_mar30_market_pre_date`: market created 2026-03-01, date 2026-03-15 → pre_mar30_crypto
- `test_for_date_pre_mar30_market_post_date`: market created 2026-03-01, date 2026-04-01 → pre_mar30_crypto (market pre-dates cutoff)
- `test_for_date_post_mar30_market_post_date`: market created 2026-04-01, date 2026-04-01 → post_mar30_crypto

**Taker fee — pre-Mar-30 regime (exponent=2):**
- `test_taker_fee_pre_mar30_reference_trade`: shares=100, price=0.5 → fee = 100 * 0.5 * 0.25 * (0.5 * 0.5)^2 = 100 * 0.5 * 0.25 * 0.0625 = 0.78125
- `test_taker_fee_pre_mar30_near_extremes`: price=0.1 → (0.1 * 0.9)^2 = 0.0081; verify fee is much smaller
- `test_taker_fee_zero_at_zero_price`: price=0 → fee=0

**Taker fee — post-Mar-30 regime (exponent=1):**
- `test_taker_fee_post_mar30_reference_trade`: shares=100, price=0.5 → fee = 100 * 0.5 * 0.072 * (0.5 * 0.5)^1 = 100 * 0.5 * 0.072 * 0.25 = 0.9
- `test_pre_and_post_regimes_differ_for_same_trade`: same trade produces different fees under each regime (AC-3)

**Maker rebate:**
- `test_maker_rebate_proportional_to_fee_equivalent`: verify rebate = (your_fee_eq / total_fee_eq) * pool
- `test_maker_rebate_zero_when_no_market_volume`: total_fee_equivalent = 0 → rebate = 0
- `test_maker_rebate_sets_estimated_flag`: rebate_estimated = True after call

**Liquidity reward:**
- `test_lr_credit_full_spread_capture`: spread=0, max_spread=0.05 → quote_score = min(bid, ask) * 1.0
- `test_lr_credit_zero_when_spread_exceeds_max`: spread >= max_spread → credit = 0
- `test_lr_credit_partial_spread`: spread = max_spread / 2 → credit = min(bid, ask) * 0.5

All numeric assertions use `Decimal` comparisons with tolerance `Decimal("0.000001")`.
