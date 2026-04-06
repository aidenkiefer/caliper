# Sprint 15: Regime Detection + Dynamic Allocation

**Version:** v2.5.0  
**Status:** Spec  
**Research sources:** `docs/research/regime-allocation.md`  
**Skills to load:** `statsmodels`, `scikit-learn`, `risk-metrics-calculation`, `quant-analyst`, `risk-manager`

---

## Overview

Markets are non-stationary. A strategy that works well in a low-volatility, trending market can lose badly in a high-volatility, toxic near-close environment. Treating all hours as equivalent squanders the system's ability to direct capital where it has the best risk-adjusted edge.

Sprint 15 builds two coupled systems:

1. **Regime Detector** — identifies discrete, measurable market states at both global (crypto-wide) and local (per-market, per-hour) scope. Outputs regime probabilities and regime labels as a real-time signal.

2. **Dynamic Allocator** — uses the regime detector's output, combined with the strategy performance matrix from Sprint 13's evaluation engine, to compute capital weights across strategies. Starts with risk parity, evolves toward Hierarchical Risk Parity (HRP) and bounded Kelly.

These systems feed directly into the fleet orchestrator in Sprint 16.

---

## Goals

1. Define measurable global and local regime states using features from Sprint 12.
2. Implement a rule-based threshold baseline regime classifier (mandatory baseline).
3. Implement a Hidden Markov Model (HMM) regime classifier for probabilistic regime probabilities.
4. Build a strategy→regime performance matrix updated continuously from Sprint 13's evaluation engine.
5. Implement the allocation engine with risk parity, HRP, and bounded Kelly methods.
6. Implement online adaptation (discounted performance estimates, blend toward baseline under uncertainty).
7. Implement the regime-specific risk management layer.

---

## Part 1: Regime Detector

### Regime Scope and Variables

#### Global Regime Vector

`G_t` captures crypto-wide conditions using features already computed by Sprint 12's `FeatureBuilder`. All inputs are features available in `FeatureSnapshot`.

| Dimension | Features used | Description |
|-----------|--------------|-------------|
| **Volatility** | `btc_rv_1m`, `btc_rv_5m`, `btc_rv_15m` | Realized vol over multiple windows |
| **Liquidity** | `spread_bps`, `book_depth_bid_5tick`, `book_depth_ask_5tick` | Market tightness and depth |
| **Trend** | `btc_momentum_5m`, `btc_sign_persistence_5m`, `btc_distance_to_open` | Directional drift |
| **Toxicity** | `vpin_proxy`, `trade_flow_imbalance_5m`, `last_5min_volume_share` | Adverse selection pressure |
| **Funding** | `btc_funding_rate`, `btc_basis_proxy` | Macro sentiment and carry |

#### Local Regime Vector

`L_{m,t}` adds market-specific event-time features for market `m`:

| Dimension | Features used | Description |
|-----------|--------------|-------------|
| **Time-to-expiry** | `time_to_close_seconds`, `near_close_flag`, `time_bucket` | When in the hour are we |
| **Microstructure state** | `spread_regime`, `order_book_imbalance`, `fill_rate_proxy` | Current book quality |
| **Fee/incentive state** | `reward_eligible`, `fee_rate_current`, `competitive_pressure` | Incentive opportunity |
| **Local toxicity** | `last_5min_volume_share`, `aggressor_buy_fraction_1m` | Per-market toxic flow |

### Regime Labels

Define 5 discrete regimes as the production classification output:

| Regime | Global conditions | Local conditions | Interpretation |
|--------|-----------------|-----------------|----------------|
| **R1: Favorable** | Low vol, trending | Early/mid hour, tight spread, low toxicity | Best hours for quoting; full allocation |
| **R2: Choppy** | Medium/high vol, directionless | Mid hour, normal spread, medium toxicity | Reduce allocation, widen spreads |
| **R3: Near-Close Toxic** | Any vol | Last 10 minutes, high toxicity, high informed fraction | Cut exposure sharply; cash-heavy |
| **R4: Connectivity Risk** | Any | Any | Heartbeat degraded; API latency > 2s | Pull all quotes immediately |
| **R5: Dead Market** | Any | Very low volume, wide spread | Market uneconomical; skip entirely |

`R4` (connectivity) is always computed first and overrides all other regimes. `R5` is checked second. `R3` is triggered by `near_close_flag = True` OR `toxicity_regime = high`.

### Classifier 1: Rule-Based Threshold (Baseline — Mandatory)

Deterministic assignment using feature thresholds. Always computed; used as fallback when HMM output has high entropy.

```python
class ThresholdRegimeClassifier:
    # Connectivity: highest priority
    R4_latency_threshold_ms: float = 2000.0
    R4_heartbeat_miss_count: int = 2
    # Dead market
    R5_max_spread_bps: float = 500.0
    R5_min_depth: Decimal = Decimal("10")
    # Near-close toxic
    R3_time_to_close_threshold_s: int = 600    # last 10 min
    R3_vpin_threshold: float = 0.65
    # Choppy
    R2_rv_5m_threshold: float = 0.002
    R2_sign_persistence_threshold: float = 0.6  # below = directionless
    # Favorable: everything else
```

### Classifier 2: Hidden Markov Model

A Gaussian HMM fitted on the `G_t` global feature vector using `hmmlearn`. Produces a **posterior probability vector** `p(z_t = k | x_{1:t})` over `K` regime states (default `K = 4`; R4 and R5 are handled by the threshold classifier and excluded from HMM).

Training:
- Fit on rolling 90-day window of 5-minute `G_t` snapshots.
- Use `K = 4` hidden states with full covariance matrices.
- Initialize with K-Means to ensure consistent state assignments.
- Retrain weekly (Sundays 00:00 UTC) or when regime quality metrics degrade (see below).

HMM states are mapped to semantic regime labels by comparing each state's mean feature vector to regime definitions. Assignment is done once per retraining and stored with the model artifact.

Practical note: the HMM produces **soft probabilities**, not hard labels. The allocator consumes the full probability vector to enable smooth weight transitions rather than discrete jumps.

### Regime Quality Metrics

Computed after each retraining and monitored continuously:

| Metric | Description | Action if bad |
|--------|-------------|---------------|
| **Posterior entropy** | `H(p(z_t))` — uniform distribution = high uncertainty | Blend toward baseline allocation |
| **Switch rate** | Regime changes per hour | Too high → ignore HMM; use threshold only |
| **Expected duration** | From HMM transition matrix | Very short durations → HMM is noisy |
| **Cross-model agreement** | Overlap between HMM and threshold labels | Low agreement → use threshold as primary |

```python
class RegimeQualityReport(BaseModel):
    computed_at: datetime
    posterior_entropy: float
    switch_rate_per_hour: float
    expected_duration_minutes: float
    agreement_with_threshold: float    # 0–1; Jaccard overlap
    quality_score: float               # composite; < 0.5 triggers fallback to threshold
```

### `RegimeDetector` Service

```
services/regime/
├── __init__.py
├── detector.py          # RegimeDetector: real-time regime inference
├── classifiers/
│   ├── threshold.py     # ThresholdRegimeClassifier
│   └── hmm.py           # HMMRegimeClassifier
├── trainer.py           # HMMTrainer: weekly refit
├── quality.py           # RegimeQualityReport computation
└── schemas.py           # RegimeState, RegimeProbabilities, RegimeQualityReport
```

`RegimeDetector` runs every 30 seconds. On each tick:
1. Compute `R4` and `R5` from threshold classifier (connectivity + dead market).
2. Compute HMM posterior `p(z_t)`.
3. Compute quality metrics.
4. If `quality_score < 0.5`, set soft weights to threshold classifier output.
5. Publish `RegimeState` to the signal bus.

```python
class RegimeState(BaseModel):
    detected_at: datetime
    market_id: Optional[str]    # None = global regime
    primary_regime: Literal["R1", "R2", "R3", "R4", "R5"]
    regime_probabilities: Dict[str, float]   # {"R1": 0.7, "R2": 0.2, ...}
    quality: RegimeQualityReport
    source: Literal["threshold", "hmm", "blended"]
```

---

## Part 2: Strategy → Regime Performance Matrix

### Data Source

Built from `pm.evaluation_reports` (Sprint 13). For each strategy `s` and regime label `k`, extract the `RegimeMetrics` slice computed by Sprint 13's evaluation engine.

### Matrix Structure

```python
class PerformanceMatrix(BaseModel):
    computed_at: datetime
    strategies: List[str]
    regimes: List[str]
    mu: Dict[str, Dict[str, Decimal]]          # mu[strategy][regime] = expected return
    sigma: Dict[str, Dict[str, Decimal]]       # sigma[strategy][regime] = return std
    drawdown: Dict[str, Dict[str, Decimal]]    # max drawdown per strategy per regime
    cost: Dict[str, Dict[str, Decimal]]        # turnover/cost per strategy per regime
    covariance: Dict[str, List[List[float]]]   # per-regime return covariance matrix
```

Updated on every new `EvaluationReport` write. The covariance matrix is computed from rolling daily returns per regime, with **Ledoit-Wolf shrinkage** applied to improve conditioning.

### Discounted Estimates (Online Adaptation)

To weight recent performance more heavily than stale history, apply exponential decay:

```
μ_discounted(t) = Σ_i w(t, t_i) * r_i    where w(t, t_i) = exp(-λ * (t - t_i))
```

Default forgetting factor `λ = ln(2) / (7 * 24)` (half-life of 7 days). This ensures regime-conditioned expectations update quickly after a regime shift.

---

## Part 3: Allocation Engine

### Methods (in order of complexity; implement all three)

#### Method 1: Risk Parity (Baseline)

Each strategy contributes equal risk to the portfolio. Weights are inversely proportional to each strategy's volatility within the current regime:

```
w_s ∝ 1 / σ_{s, current_regime}
```

Normalize to sum to 1 (or sum to the active capital fraction after cash buffer). This is the **default allocation method** until the system has ≥ 4 weeks of per-strategy history.

#### Method 2: Hierarchical Risk Parity (HRP)

Builds a hierarchical clustering tree over strategies using the regime-conditioned correlation matrix (from `PerformanceMatrix.covariance`). Allocates capital recursively, dividing risk budget at each cluster split.

Uses `riskfolio-lib` or a custom implementation following the HRP algorithm:
1. Compute correlation matrix with Ledoit-Wolf shrinkage.
2. Compute linkage matrix using single-linkage clustering.
3. Apply recursive bisection allocation.

HRP is preferred over mean-variance because it does not invert the covariance matrix and is therefore more stable with small strategy counts (4–10 strategies).

#### Method 3: Bounded Kelly

For strategies with calibrated edge estimates (e.g., the Directional Probability Model from Sprint 14), compute Kelly fractions:

```
f_s = (p * b - q) / b    where p = P(win), b = net odds, q = 1 - p
```

Apply a **fraction `f = 0.25`** of the Kelly fraction (quarter-Kelly) to limit drawdown risk. Cap any single strategy at `max_kelly_weight = 0.30`.

Only applicable to strategies where edge estimates are well-calibrated (Brier ECE < 0.05). Strategies without calibrated edge estimates use risk parity.

### Allocation Loop

Runs every 60 seconds (configurable):

```python
def allocation_tick(t, strategies, regime_state, performance_matrix, capital_budget):
    # 1. Get current regime
    regime_probs = regime_state.regime_probabilities
    entropy = compute_entropy(regime_probs)

    # 2. Compute regime-conditioned expected returns and covariance
    mu = performance_matrix.expected_mu(regime_probs, discount_factor=λ)
    Sigma = performance_matrix.expected_sigma(regime_probs, shrinkage=True)

    # 3. Choose allocation method
    if len(strategies) < 2 or history_too_short(strategies):
        weights = risk_parity(Sigma)
    elif any strategy has calibrated Kelly estimate:
        weights = blend(hrp(Sigma), bounded_kelly(mu, Sigma))
    else:
        weights = hrp(Sigma)

    # 4. Blend toward risk-parity baseline under regime uncertainty
    baseline = risk_parity(Sigma)
    alpha = confidence_from_entropy(entropy)   # 0 (uncertain) → 1 (confident)
    weights = alpha * weights + (1 - alpha) * baseline

    # 5. Apply hard risk constraints
    weights = risk_manager.enforce(weights, capital_budget)

    # 6. Compute target positions and generate orders
    allocations = capital_to_allocations(weights, capital_budget, current_prices)
    return allocations
```

### Risk Management Layer (Hard Constraints)

Applied after weights are computed; cannot be overridden:

| Constraint | Value | Description |
|-----------|-------|-------------|
| Max single strategy | 0.40 | No strategy gets > 40% of capital |
| Min cash buffer | 0.10 | Always hold ≥ 10% in cash |
| Regime R3 override | All MM strategies → 0 | Near-close: pull market-making quotes |
| Regime R4 override | All strategies → 0 | Connectivity failure: flat everything |
| Regime R5 override | Skip market | Dead market: no orders |
| Max drawdown | Kill switch at 0.15 | Portfolio-level 15% drawdown triggers pause |
| Strategy drawdown | Pause at 0.20 | Per-strategy 20% drawdown triggers pause |

**Soft constraints** (blended, not enforced absolutely):

- Volatility targeting: scale weights down if portfolio-level realized vol exceeds `target_vol = 0.10` (annualized).
- Turnover penalty: penalize large weight changes in the allocation objective to reduce transaction costs.

### `AllocationEngine` Service

```
services/allocation/
├── __init__.py
├── engine.py           # AllocationEngine: main allocation loop
├── methods/
│   ├── risk_parity.py
│   ├── hrp.py
│   └── kelly.py
├── risk_layer.py       # Hard + soft constraint enforcement
├── performance_matrix.py   # PerformanceMatrix builder + updater
└── schemas.py          # AllocationDecision, PerformanceMatrix, RegimeAllocation
```

`AllocationEngine` publishes `AllocationDecision` to the signal bus, which is consumed by the fleet orchestrator (Sprint 16).

```python
class AllocationDecision(BaseModel):
    decided_at: datetime
    regime: RegimeState
    weights: Dict[str, Decimal]         # strategy_id -> fraction of capital
    method_used: Literal["risk_parity", "hrp", "kelly", "blended"]
    confidence: float                    # from regime quality; 0 = fallback to baseline
    hard_constraints_applied: List[str]  # which hard constraints were triggered
    capital_budget: CapitalBudget        # from services/portfolio/allocator.py
```

---

## Database Tables

```sql
-- Regime state log
CREATE TABLE pm.regime_states (
    state_id       UUID DEFAULT gen_random_uuid() NOT NULL,
    detected_at    TIMESTAMPTZ NOT NULL,
    market_id      TEXT,
    primary_regime TEXT NOT NULL,
    probabilities  JSONB NOT NULL,
    quality        JSONB NOT NULL,
    source         TEXT NOT NULL,
    PRIMARY KEY (state_id, detected_at)
);
SELECT create_hypertable('pm.regime_states', 'detected_at');

-- Allocation decisions
CREATE TABLE pm.allocation_decisions (
    decision_id    UUID DEFAULT gen_random_uuid() NOT NULL,
    decided_at     TIMESTAMPTZ NOT NULL,
    weights        JSONB NOT NULL,
    method         TEXT NOT NULL,
    regime_id      UUID,
    confidence     DECIMAL,
    PRIMARY KEY (decision_id, decided_at)
);
SELECT create_hypertable('pm.allocation_decisions', 'decided_at');

-- Performance matrix snapshots
CREATE TABLE pm.performance_matrices (
    matrix_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    computed_at    TIMESTAMPTZ NOT NULL,
    matrix         JSONB NOT NULL
);
```

---

## API Endpoints

New router `services/api/routers/regime.py`:

- `GET /v1/regime/current` — returns current `RegimeState` (global).
- `GET /v1/regime/{market_id}/current` — returns current per-market `RegimeState`.
- `GET /v1/regime/history?start=&end=` — returns `List[RegimeState]`.
- `GET /v1/allocation/current` — returns current `AllocationDecision`.
- `GET /v1/allocation/history?start=&end=` — returns `List[AllocationDecision]`.
- `GET /v1/allocation/performance-matrix` — returns latest `PerformanceMatrix`.

---

## Acceptance Criteria

### AC-1: Threshold classifier
- Rule-based classifier correctly assigns R4 when connectivity metrics exceed thresholds.
- R3 is assigned when `near_close_flag = True` OR `toxicity_regime = high`.
- Unit tests cover all 5 regime assignments with explicit feature inputs.

### AC-2: HMM classifier
- HMM trains without error on 30 days of synthetic `G_t` data.
- Posterior probabilities sum to 1.0 for every tick.
- K-Means initialization produces consistent initial state assignments.

### AC-3: Regime quality monitoring
- `posterior_entropy` correctly identifies uncertain regimes (uniform posterior → entropy = log(K)).
- `agreement_with_threshold < 0.5` triggers fallback to threshold source.

### AC-4: Performance matrix
- `PerformanceMatrix` correctly computes discounted `mu` and Ledoit-Wolf shrunk `Sigma` for a known returns series.
- Discount factor halves the weight of data older than 7 days.

### AC-5: Risk parity weights
- Risk parity weights are inversely proportional to `σ_{s, regime}`.
- Weights sum to ≤ 1 (remainder is cash buffer).

### AC-6: HRP weights
- HRP weights are more balanced than naïve equal-weight on a concentrated covariance matrix.
- HRP produces the same result on identical input (determinism).

### AC-7: Hard constraints
- Regime R4 sets all strategy weights to 0 regardless of computed weights.
- Single-strategy cap of 0.40 is enforced even when HRP assigns higher weights.
- Kill switch at 15% drawdown sets all weights to 0.

### AC-8: Allocation loop
- Under uniform regime posterior (maximum uncertainty), `alpha = 0` and the output is pure risk-parity baseline.
- Under near-certain regime assignment (entropy ≈ 0), `alpha → 1` and HRP/Kelly is applied in full.

### AC-9: API
- All regime and allocation endpoints return valid JSON.
- `GET /v1/regime/current` responds within 100ms.

### AC-10: Tests
- Unit tests for `ThresholdRegimeClassifier` (all 5 regime assignments).
- Unit tests for `risk_parity`, `hrp`, `bounded_kelly` with known matrices.
- Unit tests for all hard constraint enforcement.
- Integration test: run `AllocationEngine` for 10 ticks on synthetic regime states; verify constraints are always satisfied.

---

## Out of Scope

- Training the fleet models themselves (Sprint 16).
- Cross-sectional market selection (Sprint 16).
- Wallet intelligence signals (Sprint 17).
- Equity portfolio regime detection (regime system is Polymarket-specific for now).

---

## Implementation Order

1. **Schemas** — `RegimeState`, `AllocationDecision`, `PerformanceMatrix`, `RegimeQualityReport`.
2. **Threshold classifier** — deterministic; unit-test all 5 regimes.
3. **HMM classifier** — `hmmlearn` wrapper; synthetic data test.
4. **Regime quality monitor** — entropy, switch rate, agreement score.
5. **`RegimeDetector`** — compose classifiers; publish `RegimeState`.
6. **Performance matrix** — build from Sprint 13 evaluation data; Ledoit-Wolf shrinkage.
7. **Risk parity** — implement and test.
8. **HRP** — implement and test against known matrices.
9. **Bounded Kelly** — conditional on calibrated Sprint 14 model estimates.
10. **`AllocationEngine`** — full loop with blending, hard constraints, volatility targeting.
11. **Database migration** — three new tables.
12. **API endpoints** — regime and allocation routers.

---

## Recommended Skills

| Task | Skill |
|------|-------|
| HMM implementation, time-series regime models | `statsmodels` |
| HRP, Ledoit-Wolf shrinkage, risk parity | `scikit-learn`, `risk-metrics-calculation` |
| Kelly sizing, inventory limits, kill-switch design | `risk-manager`, `quant-analyst` |
| Async allocation loop, signal bus | `async-python-patterns` |
| FastAPI router, background tasks | `fastapi-pro` |

---

## Risk Notes

- **Regime instability:** HMM can flip regimes rapidly in noisy data. The minimum-hold filter in the `RegimeDetector` (require 3 consecutive ticks in a new state before switching primary label) prevents thrashing. The threshold classifier always provides a stable fallback.
- **Covariance estimation with few strategies:** with 3–5 strategies, the covariance matrix is 3×3 to 5×5. Even with shrinkage, estimates are noisy. Use a minimum of 20 trading days per regime before trusting any covariance-based allocation.
- **Circular dependency risk:** the allocation engine reads from the evaluation engine, which reads from strategy fills, which are influenced by the allocation. Monitor for self-reinforcing feedback loops where a slightly better-performing strategy gets more capital, performs better due to better fills (not genuine edge), and gets even more capital. Add a cap on capital velocity (max weight increase of 0.10 per allocation cycle).
