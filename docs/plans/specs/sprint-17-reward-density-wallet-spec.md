# Sprint 17: Reward Density + Wallet Intelligence + Signal Aggregation

**Version:** v2.7.0  
**Status:** Spec  
**Research sources:** `docs/research/reward-density.md`  
**Skills to load:** `quant-analyst`, `blockchain-developer`, `data-engineering-data-pipeline`, `mlops-engineer`

---

## Overview

Sprint 17 is the "edge-generating" expansion layer. The fleet from Sprint 16 can find directional edges and manage inventory, but it has only partial visibility into two major information advantages available on Polymarket:

1. **Maker economics at the per-window level** — which specific hourly BTC markets have the best reward density (maker rebates + liquidity rewards per unit of competition and risk)? This is not uniform; the research shows orders-of-magnitude differences between "active" and "dead" hours.

2. **Wallet behavior** — who are the consistently profitable traders on Polymarket? What are they doing right now? Smart-money net flow is a signal the probability model does not yet capture.

Sprint 17 adds three capabilities:

1. **Reward Density Analyzer** — for each candidate market, compute expected maker incentives normalized by competition (on-chain maker HHI) and risk (BTC volatility + toxicity). This makes the cross-sectional ranker from Sprint 16 substantially more precise.

2. **Wallet Intelligence Layer** — identify top-performing wallets from on-chain data, cluster their behavior, and extract a "smart money consensus" signal.

3. **Signal Aggregation Layer** — combine model signal, wallet signal, and microstructure signal into a composite weighted signal, enabling ensemble-style decision-making across all information sources.

By v2.7, Caliper becomes a **competitive intelligence system**: capital goes where it has the best risk-adjusted edge, informed by market structure, calibrated probability, and participant behavior.

---

## Goals

1. Build the reward density scoring pipeline: compute per-market incentive estimates (maker rebates + liquidity rewards) normalized by competition and risk.
2. Compute the Herfindahl-Hirschman Index (HHI) of maker concentration from on-chain Polygon `OrderFilled` events.
3. Build the wallet intelligence layer: identify top traders, cluster behavior, extract consensus signals.
4. Build the signal aggregation layer: combine model, wallet, and microstructure signals with learned or manually specified weights.
5. Implement the model lifecycle system: promote, pause, retire, and clone strategies based on performance.

---

## Part 1: Reward Density Analyzer

### Location: `services/reward_density/`

```
services/reward_density/
├── __init__.py
├── analyzer.py         # RewardDensityAnalyzer: per-market scoring
├── incentives.py       # IncentiveEstimator: rebate pool + liquidity reward estimation
├── competition.py      # CompetitionEstimator: HHI from on-chain data
├── risk_scorer.py      # RiskScorer: volatility + toxicity composite
├── onchain/
│   ├── __init__.py
│   └── polygon_client.py   # Polygon RPC client for OrderFilled event ingestion
└── schemas.py          # RewardDensityScore, IncentiveEstimate, CompetitionMetric
```

### Incentive Estimation

For each market `i`, estimate:

```
E[Incentives_i] = E[MakerRebatePool_i] * E[s_i]
                + E[LiquidityRewardPool_i] * E[l_i]
```

#### Maker Rebate Pool

```
fee_pool_i = V_i * E[effective_fee_rate_i]

# Post-March 30 crypto parameters
effective_fee_rate = price * fee_rate * (price * (1 - price)) ** exponent
                   = price * 0.072 * (price * (1 - price))^1

rebate_pool_i = 0.20 * fee_pool_i
```

`V_i` is the rolling 7-day average volume for that hour-of-day (from `pm.trades` aggregated by hour-of-day).

`E[effective_fee_rate_i]` is estimated from the historical price distribution for that market: compute the volume-weighted average effective fee rate over recent trades.

`E[s_i]` is the expected maker share — the fraction of fee-equivalent fills you would capture. Estimated from:
- Your historical fill rate in that market (from `pm.paper_trades`).
- Market-level competition (see HHI below).

Initial estimate (before enough paper trading history): `E[s_i] = 1 / N_eff_i` (equal share among effective makers).

#### Liquidity Reward Pool

Fetched from CLOB rewards endpoints:
- `rewards_config.rate_per_day` — daily pool size in USDC.
- `rewards_max_spread` — max spread to qualify.
- `rewards_min_size` — min quote size to qualify.

Expected scoring share `E[l_i]` estimated from:
- Whether our quote policy satisfies `spread ≤ rewards_max_spread` and `size ≥ rewards_min_size`.
- Expected on-book time fraction (from heartbeat reliability and cancel/replace cadence).
- Competition: `1 / N_eff_i` as initial estimate; refined from on-chain maker share data.

If the market is not in the rewards list, `E[LiquidityRewardPool_i] = 0`.

### Competition Metric: On-Chain HHI

**Data source:** Polygon mainnet (Chain ID 137) — CTF Exchange `OrderFilled` events.

```
OrderFilled event fields:
  maker: address
  taker: address
  makerAssetId: bytes32
  takerAssetId: bytes32
  makerAmountFilled: uint256
  takerAmountFilled: uint256
  fee: uint256
```

For each market `i`, over a lookback window (default: 7 days):

1. Filter `OrderFilled` events by `makerAssetId` matching the market's YES or NO token ID.
2. Aggregate `fee` by `maker` address to get per-maker fee-equivalent `w_{i,k}`.
3. Normalize: `w_{i,k} = w_{i,k} / Σ_k w_{i,k}`.
4. Compute HHI: `HHI_i = Σ_k w_{i,k}^2`.
5. Effective number of makers: `N_eff_i = 1 / HHI_i`.

```python
class CompetitionMetric(BaseModel):
    market_id: str
    computed_at: datetime
    lookback_days: int
    hhi: Decimal
    n_eff: Decimal
    top_maker_address: Optional[str]
    top_maker_share: Optional[Decimal]
    data_source: Literal["onchain", "rewards_api_proxy"]
    is_estimate: bool       # True if using rewards API proxy (onchain data unavailable)
```

**Fallback:** If on-chain data is unavailable or too stale, use the `market_competitiveness` field from the rewards API as a proxy. Flag as `is_estimate = True`.

### Risk Scorer

```
Risk_i = z(σ_i) + λ * z(Toxicity_i)
```

- `σ_i`: realized BTC volatility for that hour (from Binance klines, `btc_rv_15m` at the time of the market open).
- `Toxicity_i`: `last_5min_volume_share` as a proxy for informed-flow risk near close.
- Both are z-scored across all candidate markets (cross-sectional normalization).
- `λ = 0.5` (configurable).

### Reward Density Score

```
Score_i = E[Incentives_i] / (Competition_i^α * Risk_i^β)
```

Default `α = 1.0`, `β = 0.5`. These are tunable.

```python
class RewardDensityScore(BaseModel):
    market_id: str
    scored_at: datetime
    expected_incentives_usd: Decimal
    maker_rebate_estimate: Decimal
    liquidity_reward_estimate: Decimal
    competition: Decimal          # N_eff_i
    risk_score: Decimal
    reward_density_score: Decimal
    alpha: Decimal
    beta: Decimal
    confidence: Literal["high", "medium", "low"]   # based on data quality
```

### Integration with Sprint 16 Ranker

`RewardDensityScore` is added as a fifth term to Sprint 16's `RankingScore`:

```
Score(m) = w_EV * EV_adj(m)
         + w_R  * EV_adj(m) / sigma(m)
         + w_L  * FeasibilityScore(m)
         + w_C  * Confidence(m)
         + w_D  * RewardDensityScore(m)   # new in Sprint 17
```

With `w_D = 0.15`, reducing other weights proportionally.

---

## Part 2: Wallet Intelligence Layer

### Location: `services/wallet_intelligence/`

```
services/wallet_intelligence/
├── __init__.py
├── profiler.py         # WalletProfiler: build wallet-level dataset
├── ranker.py           # WalletRanker: identify top performers
├── clustering.py       # WalletClusterer: behavioral clusters
├── signals.py          # WalletSignalExtractor: consensus signals
└── schemas.py          # WalletProfile, WalletCluster, WalletSignal
```

### Wallet Dataset

Built from two sources:

1. **Polymarket Data API:** `/v1/leaderboard` → `proxyWallet`, `vol`, `pnl`, `rank`. Gives a macro ranking of top traders by volume and PnL.

2. **On-chain OrderFilled events:** for each top wallet address, pull their historical fills from the CTF Exchange — `makerAssetId`, `takerAssetId`, `makerAmountFilled`, `fee`, timestamp. This gives a full trade-level history, independent of Polymarket's internal API.

```python
class WalletProfile(BaseModel):
    wallet_address: str
    profiled_at: datetime
    total_volume_usd: Decimal
    total_pnl_usd: Decimal
    win_rate: Decimal
    avg_position_size: Decimal
    preferred_markets: List[str]       # most traded condition_ids
    role: Literal["maker", "taker", "mixed"]
    activity_hours: List[int]          # hour-of-day UTC activity pattern
    last_active_at: datetime
```

### Wallet Ranker

Ranks wallets by **risk-adjusted PnL consistency** (not raw PnL, which can reflect risk-taking rather than skill):

```
WalletScore = PnL_7d / max(StdDev_daily_PnL_7d, ε) * sqrt(ActiveDays_7d)
```

The top-50 wallets by `WalletScore` are designated "smart money" and tracked continuously.

### Behavioral Clustering

Apply K-Means (k=4) on wallet feature vectors:

| Feature | Description |
|---------|-------------|
| `maker_fraction` | Fraction of volume as maker |
| `avg_time_to_close_at_entry` | When do they enter (early/late hour) |
| `avg_position_size_normalized` | Normalized by their total capital |
| `directional_bias` | Net long fraction |
| `win_rate` | Overall win rate |

Cluster labels (empirically assigned after fitting):
- **Cluster A: Informed Directionals** — takers, large positions, enter mid-to-late hour.
- **Cluster B: Efficient Makers** — mostly makers, consistent PnL, stable across hours.
- **Cluster C: Noise Traders** — small positions, random direction, low PnL.
- **Cluster D: Opportunists** — takers only in high-liquidity hours, large wins variance.

Clusters A and B are "smart money" signals. Cluster C flow is noise. Cluster D is directional but noisy.

### Wallet Signal Extraction

For each active market `m` and current time `t`, compute:

```python
class WalletSignal(BaseModel):
    market_id: str
    computed_at: datetime
    net_smart_money_position: Decimal    # net YES position among smart money wallets
    smart_money_consensus: Decimal       # -1 (bearish) to +1 (bullish)
    smart_money_activity_zscore: Decimal # recent activity vs baseline (elevated = signal)
    top_wallet_direction: Optional[Literal["long", "short", "flat"]]
    signal_confidence: Decimal
    wallet_count: int                    # number of wallets contributing
```

**Computation:**
1. For the last 2 hours, pull all `OrderFilled` events for market `m`.
2. Filter to fills by smart money wallets (top-50 leaderboard + Clusters A and B).
3. Compute net position: `sum(makerAmountFilled * maker_side_sign)`.
4. Normalize to `[-1, +1]` range as `smart_money_consensus`.
5. Z-score against rolling 30-day baseline for this hour-of-day to get `smart_money_activity_zscore`.

A high positive `smart_money_consensus` (> 0.3) with elevated activity (`zscore > 1.5`) is a bullish signal for YES tokens.

---

## Part 3: Signal Aggregation Layer

### Location: `services/signal_aggregation/`

```
services/signal_aggregation/
├── __init__.py
├── aggregator.py       # SignalAggregator: combines all signal sources
├── weighter.py         # SignalWeighter: computes signal weights
└── schemas.py          # AggregatedSignal, SignalComponent
```

### Composite Signal Formula

```
FinalSignal(m, t) = w1 * ModelSignal(m, t)
                  + w2 * WalletSignal(m, t)
                  + w3 * MicrostructureSignal(m, t)
```

| Component | Source | Default weight |
|-----------|--------|---------------|
| `ModelSignal` | `p_hat(t) - p_PM(t)` from Sprint 14 | `w1 = 0.50` |
| `WalletSignal` | `smart_money_consensus` from wallet layer | `w2 = 0.30` |
| `MicrostructureSignal` | `order_book_imbalance` from Sprint 12 | `w3 = 0.20` |

All components are z-scored before aggregation to ensure comparable scaling.

Weights are initially fixed. Sprint 17 implements a **basic weight learning loop**: after each week, compute the realized edge contribution of each signal component (correlation between the component and the subsequent 5-minute price movement). Weights are updated toward the components with higher recent predictive power, bounded by `[0.10, 0.70]` per component.

```python
class AggregatedSignal(BaseModel):
    market_id: str
    aggregated_at: datetime
    final_signal: Decimal                      # -1 to +1; positive = bullish
    model_component: Decimal
    wallet_component: Decimal
    microstructure_component: Decimal
    weights: Dict[str, Decimal]
    threshold_met: bool
    signal_strength: Literal["strong", "moderate", "weak", "none"]
```

### Integration

`AggregatedSignal` is published to the signal bus and consumed by:
- **Strategy 2 (Directional):** replaces the raw `M(t)` threshold check with the composite signal.
- **Strategy 3 (Hybrid):** uses composite signal for the directional lean decision.
- **`MarketRanker`:** incorporates `final_signal` magnitude as a confidence factor in `Confidence(m)`.

---

## Part 4: Model Lifecycle System

### Location: `services/fleet/lifecycle.py`

Automates the promotion, pausing, retiring, and cloning of strategies based on evaluation results.

```python
class LifecycleAction(str, Enum):
    PROMOTE = "promote"      # paper → live (requires human approval)
    PAUSE = "pause"          # suspend trading; keep track record
    RETIRE = "retire"        # archive; stop all tracking
    CLONE = "clone"          # create a variant with modified parameters
    DEMOTE = "demote"        # live → paper (auto-triggered by drawdown)

class LifecycleRule(BaseModel):
    rule_id: str
    strategy_id: str
    condition: str           # human-readable description of the trigger
    action: LifecycleAction
    threshold: Decimal
    lookback_days: int
    requires_human_approval: bool
```

**Default rules (all require human approval for PROMOTE/RETIRE):**

| Rule | Condition | Action |
|------|-----------|--------|
| Promote candidate | Sharpe > 1.0, win rate > 0.55, max drawdown < 0.15, ≥ 28 days paper | PROMOTE (human approval) |
| Pause underperformer | 7-day Sharpe < -0.5 OR 7-day drawdown > 0.20 | PAUSE (auto) |
| Retire zombie | Paused for > 14 days with no improvement | RETIRE (human approval) |
| Demote live | Live strategy 7-day drawdown > 0.15 | DEMOTE to paper (auto) |
| Clone for tuning | Strategy approaching retirement but promising regime slice | CLONE (human-initiated) |

The `LifecycleManager` runs daily at 00:00 UTC, evaluates all lifecycle rules, and logs proposed actions to `pm.lifecycle_events`. Auto-triggered actions (PAUSE, DEMOTE) execute immediately. Human-approval actions create a pending notification in the API.

---

## Acceptance Criteria

### AC-1: Maker rebate estimation
- `IncentiveEstimator` correctly computes `fee_pool_i` for a known historical market using the post-March 30 fee formula.
- `rebate_pool_i = 0.20 * fee_pool_i` matches expected value within 1%.

### AC-2: On-chain HHI
- `polygon_client.py` successfully fetches `OrderFilled` events for a test condition ID.
- HHI computation produces `HHI = 1.0` for a single maker (full concentration) and `HHI → 0` for many equal makers.
- `N_eff = 1 / HHI`.

### AC-3: Reward density score
- `RewardDensityScore` is higher for high-volume, low-competition markets than for low-volume, high-competition markets with the same risk.
- Score = 0 for markets not in the rewards program and with no fee-enabled taker flow.

### AC-4: Wallet profiling
- `WalletProfiler` builds a `WalletProfile` for a given wallet address from leaderboard + on-chain data.
- `role` is correctly identified as "maker" when `maker_fraction > 0.70`.

### AC-5: Clustering
- K-Means with k=4 produces stable clusters on synthetic wallet feature data (re-runs with same seed produce identical assignments).
- Cluster A has significantly higher `avg_time_to_close_at_entry` (late entry) than Cluster B (consistent throughout hour).

### AC-6: Wallet signal
- `WalletSignal.smart_money_consensus > 0.3` when smart money is predominantly net long.
- `signal_confidence` is low when fewer than 3 wallets are contributing.

### AC-7: Signal aggregation
- `FinalSignal = 0` when all components are 0.
- `AggregatedSignal` correctly applies z-scoring: each component has mean 0 and std 1 over a rolling window before weighting.
- Weight learning correctly increases `w1` when `ModelSignal` has higher recent predictive power than other components.

### AC-8: Lifecycle rules
- PAUSE rule auto-triggers and logs to `pm.lifecycle_events` when Sharpe drops below -0.5.
- PROMOTE rule creates a pending notification (does not auto-execute).
- DEMOTE rule auto-triggers when live strategy drawdown exceeds 0.15.

### AC-9: Integration
- `RewardDensityScore` is included in `RankingScore` with correct weight.
- `AggregatedSignal` replaces raw `M(t)` in Strategy 2's `generate_signals()`.

### AC-10: Tests
- Unit tests for HHI computation with edge cases (single maker, equal distribution).
- Unit tests for `IncentiveEstimator` (rebate pool, LR pool estimation).
- Unit tests for `SignalAggregator` (z-scoring, weighting, threshold logic).
- Unit tests for all lifecycle rules with synthetic evaluation data.
- Integration test: full signal aggregation pipeline from `FeatureSnapshot` + synthetic wallet data → `AggregatedSignal`.

---

## Out of Scope

- Live execution with real capital (still paper-only unless human-promoted).
- Cross-market wallet behavior (e.g., wallets trading non-BTC markets) — BTC hourly focus only.
- On-chain token balance tracking per wallet (use trade-level data only).
- Reinforcement learning or fully adaptive model mutation (future research phase).

---

## Implementation Order

1. **On-chain client** — `polygon_client.py`: `OrderFilled` event fetching + parsing.
2. **HHI computation** — `competition.py`: maker share aggregation, HHI, `N_eff`.
3. **Incentive estimator** — `incentives.py`: rebate pool + LR pool estimation.
4. **Risk scorer** — `risk_scorer.py`: BTC vol + toxicity z-score.
5. **Reward density analyzer** — `analyzer.py`: composite score; integration into Sprint 16 ranker.
6. **Wallet profiler** — `profiler.py`: leaderboard + on-chain data; `WalletProfile`.
7. **Wallet ranker** — `ranker.py`: `WalletScore`, top-50 designation.
8. **Wallet clustering** — `clustering.py`: K-Means, cluster label assignment.
9. **Wallet signal extractor** — `signals.py`: consensus computation.
10. **Signal aggregator** — `aggregator.py`: composite signal, weight learning.
11. **Lifecycle manager** — `lifecycle.py`: rule engine, notifications.
12. **Database migration** — new tables for reward density, wallet profiles, lifecycle events.
13. **API endpoints** — reward density, wallet intelligence, aggregated signal, lifecycle.

---

## Database Tables

```sql
-- Reward density scores
CREATE TABLE pm.reward_density_scores (
    score_id       UUID DEFAULT gen_random_uuid() NOT NULL,
    market_id      TEXT NOT NULL,
    scored_at      TIMESTAMPTZ NOT NULL,
    score          JSONB NOT NULL,
    PRIMARY KEY (score_id, scored_at)
);
SELECT create_hypertable('pm.reward_density_scores', 'scored_at');

-- Wallet profiles
CREATE TABLE pm.wallet_profiles (
    wallet_address TEXT NOT NULL,
    profiled_at    TIMESTAMPTZ NOT NULL,
    profile        JSONB NOT NULL,
    cluster_id     INTEGER,
    PRIMARY KEY (wallet_address, profiled_at)
);

-- Wallet signals
CREATE TABLE pm.wallet_signals (
    signal_id      UUID DEFAULT gen_random_uuid() NOT NULL,
    market_id      TEXT NOT NULL,
    computed_at    TIMESTAMPTZ NOT NULL,
    signal         JSONB NOT NULL,
    PRIMARY KEY (signal_id, computed_at)
);
SELECT create_hypertable('pm.wallet_signals', 'computed_at');

-- Aggregated signals
CREATE TABLE pm.aggregated_signals (
    signal_id      UUID DEFAULT gen_random_uuid() NOT NULL,
    market_id      TEXT NOT NULL,
    aggregated_at  TIMESTAMPTZ NOT NULL,
    signal         JSONB NOT NULL,
    PRIMARY KEY (signal_id, aggregated_at)
);
SELECT create_hypertable('pm.aggregated_signals', 'aggregated_at');

-- Lifecycle events
CREATE TABLE pm.lifecycle_events (
    event_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id    TEXT NOT NULL,
    event_type     TEXT NOT NULL,
    triggered_at   TIMESTAMPTZ NOT NULL,
    rule_id        TEXT NOT NULL,
    approved       BOOLEAN,
    approved_at    TIMESTAMPTZ,
    notes          TEXT
);
```

---

## Recommended Skills

| Task | Skill |
|------|-------|
| On-chain event fetching, Polygon EIP-712, CTF Exchange | `blockchain-developer` |
| Reward pool modeling, fee curve analysis, competition metrics | `quant-analyst` |
| Signal aggregation, weight learning, feature pipeline design | `data-engineering-data-pipeline` |
| Model lifecycle management, drift detection | `mlops-engineer` |
| K-Means clustering, HMM, statistical tests | `scikit-learn`, `statsmodels` |

---

## Risk Notes

- **On-chain data latency:** Polygon block times are ~2 seconds, but indexing `OrderFilled` events at scale requires either a dedicated node or a third-party indexer (Dune, The Graph). Use The Graph or Dune as an initial backend; plan migration to a local archive node if latency exceeds 60 seconds.
- **Wallet privacy and gaming:** sophisticated wallets may route trades through multiple addresses to avoid detection. The HHI and wallet intelligence metrics are best-effort estimates, not ground truth. Treat `signal_confidence = low` conservatively.
- **Weight learning instability:** the composite signal weight learning loop can oscillate if the lookback window is too short or market conditions shift. Always bound weights `[0.10, 0.70]` and apply a maximum weekly weight change of 0.05 per component.
- **Lifecycle automation risk:** auto-PAUSE and auto-DEMOTE are safe (they reduce exposure). Auto-PROMOTE must always require human approval — never allow the system to promote a strategy to live trading without explicit sign-off.
