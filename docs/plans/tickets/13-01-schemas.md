# Ticket 13-01: Schemas

## Task

Define all Pydantic models and dataclasses for Sprint 13 — both the simulation engine (`services/simulation/schemas.py`) and evaluation engine (`services/evaluation/schemas.py`). Create the module scaffolding for both new services.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/simulation/__init__.py`
- Create: `services/simulation/schemas.py`
- Create: `services/simulation/replay/__init__.py`
- Create: `services/simulation/orderbook/__init__.py`
- Create: `services/simulation/execution/__init__.py`
- Create: `services/simulation/adverse/__init__.py`
- Create: `services/evaluation/__init__.py`
- Create: `services/evaluation/schemas.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (all schema sections)
- `packages/common/polymarket_schemas.py` (existing Pydantic patterns, FeatureSnapshot)

### Optional read-only references
- `packages/common/schemas.py` (PriceBar, Order patterns)

## Done criteria

### `services/simulation/schemas.py`

**`SimEvent`** (BaseModel):
- `event_id: str`
- `timestamp: datetime`
- `event_type: Literal["snapshot", "trade", "cancel"]`
- `market_id: str`
- `token_id: str`
- `payload: Dict[str, Any]`

**`SimOrder`** (BaseModel):
- `order_id: str`
- `market_id: str`
- `token_id: str`
- `side: Literal["BUY", "SELL"]`
- `order_type: Literal["taker", "maker"]`  # taker=marketable limit, maker=post-only
- `price: Decimal`
- `size: Decimal`
- `submit_time: datetime`
- `post_only: bool = False`

**`SimFill`** (BaseModel):
- `fill_id: str`
- `order_id: str`
- `market_id: str`
- `token_id: str`
- `side: Literal["BUY", "SELL"]`
- `fill_price: Decimal`
- `fill_size: Decimal`
- `fill_time: datetime`
- `maker_fill: bool`  # True if this side was the maker
- `slippage_vs_mid: Decimal`  # fill_price - mid_at_submit for taker orders
- `mid_at_fill: Decimal`
- `rebate_estimated: bool = False`  # True if maker rebate is an estimate

**`PnLComponents`** (dataclass):
- `spread_capture: Decimal`
- `inventory_drift: Decimal`
- `maker_rebate: Decimal`
- `liquidity_reward: Decimal`
- `taker_fee: Decimal`
- `ops_cost: Decimal`

  Property: `total: Decimal` = sum of all components

**`SimResult`** (BaseModel):
- `run_id: str`
- `strategy_id: str`
- `market_id: str`
- `start_time: datetime`
- `end_time: datetime`
- `fills: List[SimFill]`
- `pnl_components: PnLComponents` (serialized as dict)
- `total_pnl: Decimal`
- `fill_count: int`
- `fill_rate: Decimal`  # filled / submitted
- `maker_fill_rate: Decimal`
- `config: Dict[str, Any]`  # serialized ExecutionConfig

### `services/evaluation/schemas.py`

**`PnLComponents`** — re-export from `services.simulation.schemas` (same type)

**`StrategyMetrics`** (BaseModel):
- All fields from spec § StrategyMetrics Schema
- `strategy_id: str`
- `period_start: datetime`, `period_end: datetime`
- `total_pnl: Decimal`
- `pnl_components: Dict[str, Decimal]`  # serialized PnLComponents
- `sharpe_ratio: Decimal`
- `sortino_ratio: Decimal`
- `calmar_ratio: Decimal`
- `win_rate: Decimal`
- `profit_factor: Decimal`
- `max_drawdown: Decimal`
- `max_drawdown_duration_hours: int`
- `consistency_score: Decimal`
- `stability_score: Decimal`
- `total_volume_usd: Decimal`
- `fill_rate: Decimal`
- `maker_fill_rate: Decimal`
- `regret_vs_hold_cash: Decimal`
- `regret_vs_buy_and_hold: Decimal`
- `regret_vs_random: Decimal`
- `sharpe_confidence: Literal["low", "medium", "high"] = "high"`  # "low" if < 20 data points (AC-7)
- `data_points: int`  # number of daily PnL observations used

**`RegimeMetrics`** (BaseModel):
- `strategy_id: str`
- `regime: str`  # e.g. "vol_regime=high"
- `metrics: StrategyMetrics`
- `sample_hours: int`

**`StrategyRanking`** (BaseModel):
- `strategy_id: str`
- `rank: int`
- `composite_score: Decimal`

**`EvaluationReport`** (BaseModel):
- `report_id: UUID`
- `generated_at: datetime`
- `strategy_ids: List[str]`
- `period_start: datetime`
- `period_end: datetime`
- `per_strategy: Dict[str, StrategyMetrics]`
- `regime_breakdown: Dict[str, List[RegimeMetrics]]`
- `rankings: List[StrategyRanking]`
- `baseline_comparison: Dict[str, Decimal]`  # strategy_id → regret vs best baseline

### Module scaffolding
All `__init__.py` files have appropriate module docstrings and export the primary types from their module. `services/simulation/__init__.py` exports `SimEvent`, `SimOrder`, `SimFill`, `SimResult`, `PnLComponents`. `services/evaluation/__init__.py` exports `StrategyMetrics`, `RegimeMetrics`, `EvaluationReport`.
