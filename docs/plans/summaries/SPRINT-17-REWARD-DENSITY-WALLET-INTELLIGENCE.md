# Sprint 17: Reward density + wallet intelligence + signal aggregation — summary

**Version:** v2.7.0  
**Status:** Complete (merged to `main`, 2026-04-12).  
**Spec:** [sprint-17-reward-density-wallet-spec.md](../specs/sprint-17-reward-density-wallet-spec.md)  
**Plan:** [docs/superpowers/plans/2026-04-11-sprint-17-reward-density-wallet-intelligence.md](../../superpowers/plans/2026-04-11-sprint-17-reward-density-wallet-intelligence.md)

## What shipped

### `services/reward_density/` — on-chain maker incentive scoring

- **`onchain/polygon_client.py`** — Polygon RPC client reading `OrderFilled` events from the Polymarket CLOB contract. `web3.py` import is guarded; degrades to empty list if library not installed.
- **`competition.py`** — `CompetitionEstimator`: computes **HHI** (Herfindahl-Hirschman Index) and `N_eff = 1/HHI` from on-chain fill events. Single-maker market → HHI = 1.0; equal N makers → N_eff = N.
- **`incentives.py`** — `IncentiveEstimator`: models maker rebate (20% of fee pool) and liquidity-reward pool eligibility using the **post-March-30 fee formula**. Outputs `IncentiveEstimate` with `expected_total_usd`, `maker_rebate_estimate`, `liquidity_reward_estimate`.
- **`risk_scorer.py`** — `RiskScorer`: cross-sectional z-score of BTC realised volatility and order-flow toxicity, normalized to `[0, 1]`.
- **`analyzer.py`** — `RewardDensityAnalyzer`: combines incentive, competition, and risk into a single `reward_density_score = incentives / (competition × risk_score)`. Also exposes `confidence` ("high" for real on-chain data, "medium"/"low" for estimates).
- **`schemas.py`** — Pydantic models: `RewardDensityScore`, `CompetitionMetric`, `IncentiveEstimate`.
- **Ranker integration** — `services/ranking/score.py` gains a 5th weight term `w_D × reward_density_score`; `services/ranking/schemas.py` adds `reward_density_score` field to `MarketScore`.

### `services/wallet_intelligence/` — smart-money profiling and signals

- **`schemas.py`** — Pydantic models: `WalletProfile` (address, role, fill stats, cluster), `WalletSignal` (consensus, zscore, confidence, count, direction).
- **`profiler.py`** — `WalletProfiler`: derives maker/taker role (fraction > 0.70 → `"maker"`), computes fill-count, avg size, win rate from on-chain events.
- **`ranker.py`** — `WalletRanker`: ranks wallets by a composite score of volume × win_rate × recency.
- **`clustering.py`** — `WalletClusterer`: KMeans (k=4, fixed seed) over `[avg_size, win_rate, fill_count]`. Stable label assignment with the same seed across runs.
- **`signals.py`** — `WalletSignalExtractor`: takes a `smart_money_addresses` set and a list of `OrderFilledEvent`s; computes `smart_money_consensus` (net long fraction, −1 to +1), activity z-score, signal confidence (low < 3 wallets), wallet count, top-wallet direction.

### `services/signal_aggregation/` — composite signal aggregator

- **`schemas.py`** — `AggregatedSignal`: `final_signal` (−1 to +1), `model_component`, `wallet_component`, `microstructure_component` (all z-scored), `weights`, `threshold_met`, `signal_strength` ("strong" ≥ 0.7 / "moderate" ≥ 0.4 / "weak" ≥ threshold / "none").
- **`weighter.py`** — `SignalWeighter`: updates `model`/`wallet`/`micro` weights from rolling correlation scores. Bounds: `[0.10, 0.70]` per component; max weekly change = 0.05; double clamp-then-normalise to maintain bounds post-normalisation. Ignores unknown keys in `correlation_scores`.
- **`aggregator.py`** — `SignalAggregator`: z-scores each component against its history window (population std; returns 0 when variance = 0), applies weighted sum, clamps to `[−1, +1]`, classifies `signal_strength` using Decimal comparisons throughout.

### `services/fleet/lifecycle.py` — model lifecycle manager

- **`LifecycleManager.evaluate()`**: produces `LifecycleEvent` objects from `StrategyEvaluationSnapshot` lists. Rules (in priority order):
  - **DEMOTE** (auto): live strategy, 7d drawdown > 0.15 → demote + skip other rules.
  - **PAUSE** (auto): 7d Sharpe < −0.5 or 7d drawdown > 0.20.
  - **RETIRE** (human approval): paused > 14 days.
  - **PROMOTE** (human approval): Sharpe > 1.0, win_rate > 0.55, max_drawdown < 0.15, ≥ 28 paper days.

### `services/data/alembic/versions/014_create_sprint17_tables.py` — migration 014

Five new tables in the `pm` schema:

| Table | Type | Purpose |
|---|---|---|
| `pm.reward_density_scores` | TimescaleDB hypertable | Per-market reward density scores (JSONB payload) |
| `pm.wallet_profiles` | Regular table | Point-in-time wallet snapshots with cluster assignment |
| `pm.wallet_signals` | TimescaleDB hypertable | Smart-money consensus signals per market |
| `pm.aggregated_signals` | TimescaleDB hypertable | Composite (model + wallet + micro) aggregated signals |
| `pm.lifecycle_events` | Regular table | Strategy lifecycle audit log (approve/reject workflow) |

### API — four new routers (all DB-backed, not mock)

| Endpoint | Router | Table |
|---|---|---|
| `GET /v1/reward-density/scores` | `routers/reward_density.py` | `pm.reward_density_scores` |
| `GET /v1/wallet-intelligence/signals` | `routers/wallet_intelligence.py` | `pm.wallet_signals` |
| `GET /v1/signal-aggregation/signals` | `routers/signal_aggregation.py` | `pm.aggregated_signals` |
| `GET /v1/lifecycle/events` | `routers/lifecycle.py` | `pm.lifecycle_events` |

All endpoints use `DISTINCT ON (market_id)` for latest-per-market; support `limit` query param (1–200); return 503 on DB error. Tables are empty until the scorer/extractor/aggregator pipelines write to them.

### Strategy integration

- **`poly_directional_v1.py`** — `on_aggregated_signal(signal: AggregatedSignal)`: if signal is set and `threshold_met=False`, `generate_signals()` suppresses output (returns `[]`) even when mispricing exceeds the raw threshold.
- **`poly_hybrid_v1.py`** — same method added; `final_signal` biases bid/ask factors for directional lean when `threshold_met=True`.

### Tests

- Unit: `tests/unit/reward_density/` (competition, incentives, analyzer), `tests/unit/wallet_intelligence/` (clustering, signals), `tests/unit/signal_aggregation/` (aggregator), `tests/unit/fleet/` (lifecycle) — 34 tests.
- Integration: `tests/integration/test_sprint17_pipeline.py` — 2 end-to-end tests (reward density pipeline + signal aggregation pipeline).

## Deferred / follow-up

- **Populate the new tables**: none of the scorer/extractor/aggregator services have a production scheduler or session loop writing to `pm.reward_density_scores`, `pm.wallet_signals`, `pm.aggregated_signals`, or `pm.lifecycle_events` yet. The pipelines exist as Python libraries; a driver (cron, session orchestrator, or CLI) is needed to wire them up.
- **Lifecycle approval workflow**: `LifecycleEvent.requires_human_approval` is generated correctly, but there is no API endpoint or UI to approve/reject PROMOTE/RETIRE events.
- **`poly_hybrid_v1` lean depth**: the ±10% bid/ask factor adjustment is a placeholder; calibrate against live data once signals are populated.

## Boundaries

- **Polygon RPC calls** are guarded behind `web3.py`; if the dependency is not installed the client returns an empty list without error.
- **No equity stack changes**: reward density and wallet intelligence are Polymarket-specific components; the equity `Strategy` / backtest / Alpaca path is untouched.

## References

- **Spec:** `docs/plans/specs/sprint-17-reward-density-wallet-spec.md`
- **API shapes:** `services/reward_density/schemas.py`, `services/wallet_intelligence/schemas.py`, `services/signal_aggregation/schemas.py`, [api-contracts.md](../../api-contracts.md)
- **Progress:** [PROGRESS.md](../PROGRESS.md) (`v2.7.0`)
