# Sprint 16: Cross-Sectional Ranking + Model Fleet

**Version:** v2.6.0  
**Status:** Spec  
**Research sources:** `docs/research/cross-sectional.md`, `docs/research/reward-density.md`  
**Skills to load:** `quant-analyst`, `backtesting-frameworks`, `risk-manager`, `async-python-patterns`, `frontend-design`

---

## Overview

By Sprint 16, the system has:
- A unified feature pipeline (Sprint 12) producing `FeatureSnapshot` in real time.
- A CLOB simulation and evaluation engine (Sprint 13) scoring each strategy per regime.
- A calibrated BTC probability model (Sprint 14) producing real-time `p_hat(t)` and `M(t)`.
- A regime detector and dynamic allocator (Sprint 15) that knows when and how much to trade.

Sprint 16 assembles these into a **working model fleet**: multiple competing strategies executing in parallel (paper trading), dynamically allocated capital based on regime-conditioned performance. It also builds the **cross-sectional market ranker** — a system that continuously scores all available Polymarket BTC hourly windows and selects the best ones to trade, rather than trading any market by default.

This sprint delivers the v2.6 milestone: a competition-driven, multi-model system with per-model dashboards.

---

## Goals

1. Build the cross-sectional market ranker: score all candidate markets by expected edge, execution feasibility, and risk.
2. Implement the fleet of 3–4 competing strategies as `Strategy` subclasses.
3. Build the fleet orchestrator: route feature data to each strategy, collect signals, apply allocation weights.
4. Wire the full pipeline end-to-end in paper trading mode.
5. Extend the dashboard with per-model performance panels, signal logs, and regime overlays.

---

## Part 1: Cross-Sectional Market Ranker

### Location: `services/ranking/`

```
services/ranking/
├── __init__.py
├── ranker.py           # MarketRanker: scores and ranks all candidate markets
├── universe.py         # UniverseBuilder: discovers and filters eligible markets
├── edge.py             # EdgeEstimator: mispricing, cost-adjusted EV
├── feasibility.py      # FeasibilityScorer: depth, spread, queue, fill rate
├── score.py            # RankingScore: composite score computation
└── schemas.py          # CandidateMarket, MarketScore, RankedUniverse
```

### Universe Definition

The `UniverseBuilder` runs hourly. It discovers all active Polymarket BTC hourly markets via the Gamma API and applies eligibility filters before any scoring:

**Inclusion filters:**
- `active = True` and not yet closed.
- `feesEnabled = True` OR reward-eligible (either provides economic incentive).
- Market category is BTC hourly (1H Up/Down); 5m and 15m Chainlink markets are excluded unless explicitly enabled.

**Exclusion filters (liquidity gates):**
- Rolling 24h volume < $10,000 USD (configurable `min_volume_usd`).
- Best bid-ask spread > 3% of midpoint (configurable `max_spread_pct`).
- Both sides of the same market are not selected simultaneously (YES and NO for the same condition cannot both appear in the top-N).

### Edge Estimator

For each candidate market `m`, computes the **cost-adjusted expected value** of trading:

```
EV_raw(m) = p_hat(m, t) - p_PM(m, t)       # mispricing from Sprint 14 model

EV_adj(m) = EV_raw(m)
           - spread(m, t) / 2               # half-spread cost
           - slippage_estimate(m, size)     # estimated book depth slippage
           - fee_edge(p, size)              # taker fee cost if applicable
```

`p_hat(m, t)` is the Sprint 14 probability model applied to market `m`'s current `FeatureSnapshot`. For markets where the probability model has no direct coverage (e.g., a market in an unusual hour-of-day bucket), a fallback estimate `p_hat = 0.5` is used and flagged as `low_confidence = True`.

A **latency decay penalty** is applied when model predictions are older than `staleness_threshold = 30s`:

```
EV_adj(m) *= exp(-decay_rate * staleness_seconds)
```

### Feasibility Scorer

Scores the executability of trading market `m`, independent of the expected return:

```
LiquidityScore(m) = (book_depth_bid_5tick + book_depth_ask_5tick) / (spread_bps * btc_rv_5m + ε)

FillProbability(m) = estimate based on recent trade intensity and queue position proxy

FeasibilityScore(m) = normalize(LiquidityScore) * FillProbability(m)
```

The feasibility score is bounded `[0, 1]`. A score < 0.2 triggers exclusion (not just downweighting).

### Ranking Function

Composite score combining EV, risk, liquidity, and model confidence:

```
Score(m) = w_EV * EV_adj(m)
         + w_R  * EV_adj(m) / (sigma(m) + ε)    # Sharpe-like component
         + w_L  * FeasibilityScore(m)             # liquidity factor
         + w_C  * Confidence(m)                   # model reliability
```

Default weights: `w_EV = 0.40`, `w_R = 0.30`, `w_L = 0.20`, `w_C = 0.10`. Weights are configurable per deployment.

Markets with `EV_adj < 0` are capped to a score of 0 (no-trade; never score negative markets as candidates).

### Selection Logic

From the ranked list:

1. Take the top `N` markets (default `N = 3`; configurable via `max_active_markets`).
2. Apply diversification constraint: skip markets where `|time_to_close - other_selected_market.time_to_close| < 600s` (avoid near-duplicate timing exposure).
3. Capital allocation to selected markets follows Sprint 15's `AllocationEngine` output.
4. Implement a cooldown: a market must stay below the top-N for 3 consecutive ranking cycles before it is exited.

### Re-Ranking Cadence

The `MarketRanker` runs every 60 seconds. Score updates are published to the signal bus. The fleet orchestrator subscribes and adjusts active markets accordingly.

```python
class RankedUniverse(BaseModel):
    ranked_at: datetime
    total_candidates: int
    selected_markets: List[MarketScore]
    excluded_markets: List[str]              # market_ids excluded by filters
    ranking_method: str
    cooldown_protected: List[str]            # markets in cooldown period
```

---

## Part 2: Model Fleet

### Fleet Composition

Implement 4 strategies as `Strategy` subclasses (from `packages/strategies/base.py`). All emit `UnifiedSignal` and have `market_type = MarketType.PREDICTION`.

---

#### Strategy 1: Microstructure Maker (Baseline)

**Strategy ID:** `poly_mm_v2`  
**Type:** `SignalType.MARKET_MAKING`  
**Basis:** Evolution of the existing `PolymarketMMStrategy`.

Improvements over V1:
- **Inventory skew:** center `c_t = m_t - φ * q_t` where `φ` is calibrated from Sprint 13 simulation to minimize adverse selection losses.
- **Spread widening near close:** parameterize `δ` (quote distance from midpoint) as a function of `time_to_close_seconds`. Widen by 2× in the last 10 minutes.
- **Fee-curve-aware sizing:** adjust quote size to maximize `FeeScore = min(bid_size, ask_size) * max(0, 1 - spread / reward_max_spread)` when reward-eligible, without compromising fill rates.
- **Regime override:** suppress quoting when `RegimeState.primary_regime == R3`.

Signals emitted:
```python
UnifiedSignal(
    direction="none",
    signal_type=SignalType.MARKET_MAKING,
    metadata={
        "bid_price": ..., "ask_price": ...,
        "bid_size": ..., "ask_size": ...,
        "inventory_skew": ...,
    }
)
```

---

#### Strategy 2: Directional Probability Model

**Strategy ID:** `poly_directional_v1`  
**Type:** `SignalType.DIRECTIONAL`  
**Basis:** Sprint 14 probability model. Emits a BUY YES or BUY NO signal when `|M(t)| > θ(t)`.

Logic:
1. Subscribe to `ProbabilityPredictor` output.
2. Compare `|M(t)|` to `threshold(t)` (fee + spread + ε).
3. If threshold is met and `RegimeState ∈ {R1, R2}` (skip R3/R4/R5):
   - `M(t) > θ`: emit `direction = "long"` (BUY YES).
   - `M(t) < -θ`: emit `direction = "short"` (BUY NO).
4. Respect a position cooldown: do not re-enter same direction within `min_hold_seconds = 120`.

Risk check (in `risk_check()`):
- Convert signal to a taker order sized by `confidence * max_position_usd / p_current`.
- Cap at `max_position_usd` per market (from `CapitalBudget`).
- Reject if `time_to_close < 120s` (too late; adverse selection risk too high).

---

#### Strategy 3: Hybrid Model

**Strategy ID:** `poly_hybrid_v1`  
**Type:** `SignalType.HYBRID`  
**Basis:** Combines microstructure maker + directional signal.

Logic:
- Default behavior: quote both sides as market maker (like Strategy 1).
- When directional signal from Strategy 2 would trigger:
  - **If making on the favorable side:** aggressively tighten bid (if going long) or ask (if going short); post larger maker order on the favorable side.
  - **If making on the unfavorable side:** cancel the unfavorable side; only quote the favorable direction.
- The hybrid strategy never takes liquidity — it adjusts maker positioning rather than crossing the spread.

This is the "Only quote aggressively when directional edge exists" design from `expansion.md §3.3`.

Emits `UnifiedSignal(signal_type=SignalType.HYBRID)` with metadata containing both the MM bid/ask and the directional lean.

---

#### Strategy 4: Regime-Aware Model

**Strategy ID:** `poly_regime_v1`  
**Type:** `SignalType.DIRECTIONAL` (varies by regime)  
**Basis:** Switches behavior based on the current `RegimeState`.

| Regime | Behavior |
|--------|----------|
| R1 (Favorable) | Full market-making + directional overlay (same as Strategy 3) |
| R2 (Choppy) | Wider spreads, smaller size, no directional bets |
| R3 (Near-Close Toxic) | Cancel all quotes; hold position if any; no new orders |
| R4 (Connectivity) | Cancel everything immediately |
| R5 (Dead Market) | Skip; ABSTAIN signal |

Internal `RegimeState` is consumed from the signal bus (published by Sprint 15's `RegimeDetector`). Regime switches trigger an immediate requote cycle.

---

### Fleet Orchestrator

**Location:** `services/fleet/orchestrator.py`

The fleet orchestrator is the main event loop for the live fleet. It:

1. Subscribes to:
   - `FeatureBuilder` output (per market).
   - `RankedUniverse` from `MarketRanker`.
   - `AllocationDecision` from `AllocationEngine`.
   - `RegimeState` from `RegimeDetector`.
   - `PredictionRecord` from `ProbabilityPredictor`.

2. Routes data to each strategy's `on_market_data()` and triggers `generate_signals()`.

3. Passes signals through the `Allocator` (`services/portfolio/allocator.py`) with budget weights from `AllocationDecision`.

4. Routes `AllocationResult` through `GlobalRiskManager` pre-trade check.

5. Dispatches approved orders to `PolymarketAdapter` (execution).

6. Records all fills to `pm.trades` and publishes to the evaluation engine.

```
services/fleet/
├── __init__.py
├── orchestrator.py     # FleetOrchestrator: main loop
├── registry.py         # StrategyRegistry: load/instantiate fleet strategies
└── schemas.py          # FleetStatus, StrategyStatus
```

### Paper Trading Mode

All fleet strategies run in paper mode until explicitly promoted to live (requires manual override). In paper mode:

- Orders are sent to `PolymarketAdapter.place_order()` in a dry-run mode (no actual submission to CLOB).
- Simulated fills are generated by `SimulationRunner` using live market data.
- PnL is tracked in `pm.paper_trades` table.
- Strategies accumulate a track record for Sprint 15's evaluation engine.

A minimum of 4 weeks of paper trading with positive cumulative Sharpe is required before any strategy is considered for live promotion (human approval required).

---

## Part 3: Dashboard Extensions

### New Dashboard Panels

Added to `apps/dashboard/` under the existing Model Observatory:

#### Panel 1: Market Ranker View
- Live table of all candidate markets with columns: `market`, `score`, `adj_EV`, `feasibility`, `spread`, `volume`, `selected`.
- Highlight selected (active) markets.
- Shows `ranked_at` timestamp and staleness indicator.

#### Panel 2: Fleet Overview
- One card per strategy: `strategy_id`, current status (active/paused/cooldown), 24h PnL, Sharpe (7d rolling), fill rate, current allocation weight.
- Color-coded by regime regime alignment.

#### Panel 3: Per-Strategy Signal Log
- Rolling last 50 signals per strategy: timestamp, market, direction/type, confidence, action taken (executed/rejected/abstained), fill price.

#### Panel 4: Regime Timeline
- Stacked timeline chart showing `RegimeState.primary_regime` over the last 24 hours.
- Overlay: allocation weights per strategy at each time point.

#### Panel 5: Cross-Strategy Comparison
- Side-by-side metric table: strategy vs baseline for Sharpe, Sortino, win rate, max drawdown, profit factor.

---

## Acceptance Criteria

### AC-1: Market ranker
- `MarketRanker` correctly computes `Score(m)` for a set of synthetic markets with known `EV_adj`, `FeasibilityScore`, and `Confidence`.
- Markets with `EV_adj < 0` score 0.
- Selection logic never selects both YES and NO of the same market simultaneously.

### AC-2: Universe filters
- Markets below `min_volume_usd` are excluded before scoring.
- Markets above `max_spread_pct` are excluded before scoring.

### AC-3: Fleet strategy instantiation
- All 4 strategies instantiate without error.
- All declare `market_type = MarketType.PREDICTION` and are enforced by `Strategy.__init_subclass__`.
- All `generate_signals()` return `List[UnifiedSignal]` with correct fields.

### AC-4: Hybrid strategy behavior
- When `M(t) > θ`, the hybrid strategy widens the ask and tightens the bid (verifiable from emitted signal metadata).
- The hybrid strategy never emits a taker order.

### AC-5: Regime-aware strategy
- `poly_regime_v1` emits `ABSTAIN` in R5 and cancels all quotes in R4.
- Regime switch from R1 to R3 triggers a cancel-all signal within 1 tick.

### AC-6: Fleet orchestrator
- Full pipeline (FeatureSnapshot → Strategy → Allocator → GlobalRiskManager → Adapter) completes end-to-end without error in paper mode.
- All approved orders are logged to `pm.paper_trades`.

### AC-7: Paper mode
- No real orders reach the CLOB in paper mode.
- `pm.paper_trades` accumulates fills from the simulation engine.

### AC-8: Dashboard panels
- Market Ranker View displays live `RankedUniverse` data.
- Fleet Overview cards display correct per-strategy PnL and Sharpe from the evaluation engine.
- Regime Timeline renders correct labels.

### AC-9: Ranking cadence
- `MarketRanker` produces a new `RankedUniverse` within 5 seconds of being triggered.
- Cooldown protection prevents a market from being re-entered within 3 ranking cycles of falling below the threshold.

### AC-10: Tests
- Unit tests for `EdgeEstimator`, `FeasibilityScorer`, and composite `RankingScore` with explicit input/output assertions.
- Unit tests for each strategy's `generate_signals()` with synthetic `FeatureSnapshot` input.
- Integration test: fleet orchestrator runs for 5 ticks in paper mode; verify fills are logged.

---

## Out of Scope

- Live (funded) trading (paper only in this sprint).
- Wallet intelligence signals (Sprint 17).
- Composite signal aggregation across multiple signal sources (Sprint 17).
- On-chain HHI competition metric (Sprint 17).

---

## Implementation Order

1. **Cross-sectional schemas** — `CandidateMarket`, `MarketScore`, `RankedUniverse`.
2. **Universe builder** — Gamma API integration, eligibility filters.
3. **Edge estimator** — cost-adjusted EV computation; latency decay.
4. **Feasibility scorer** — `LiquidityScore`, `FillProbability`.
5. **Ranking function + selection** — composite score, top-N, cooldown.
6. **Strategy 1 (MM v2)** — inventory skew, spread-widening near close.
7. **Strategy 2 (Directional)** — P model consumer, threshold rule.
8. **Strategy 3 (Hybrid)** — MM + directional lean.
9. **Strategy 4 (Regime-Aware)** — regime-switching behavior.
10. **Fleet orchestrator** — full pipeline wiring.
11. **Paper trading mode** — `pm.paper_trades` logging, dry-run adapter.
12. **Dashboard panels** — 5 new panels (Market Ranker, Fleet Overview, Signal Log, Regime Timeline, Comparison).

---

## Recommended Skills

| Task | Skill |
|------|-------|
| Edge estimation, fee-adjusted EV, Kelly sizing | `quant-analyst` |
| CLOB fill simulation, walk-forward evaluation of fleet | `backtesting-frameworks` |
| Position limits, drawdown controls, fleet kill switch | `risk-manager` |
| Async fleet orchestrator, signal bus | `async-python-patterns` |
| Dashboard panels, charts, operational clarity | `frontend-design`, `ui-ux-pro-max` |

---

## Risk Notes

- **Correlation within fleet:** Strategy 1, 2, 3, and 4 all trade the same markets. If they share too much signal (they all read from `FeatureSnapshot` and `ProbabilityPredictor`), their returns may be highly correlated, defeating the purpose of the fleet. Monitor the inter-strategy return correlation matrix; if average correlation exceeds 0.7, consolidate or differentiate the strategies before going live.
- **Market ranker over-selection of same hour:** the ranker may consistently select the same high-volume hour (e.g., 8–9AM ET). Add an hour-of-day diversification constraint to avoid full capital concentration in one market repeatedly.
- **Paper trading fidelity:** simulated fills from Sprint 13's `SimulationRunner` are a close-but-not-exact proxy for real fills. Flag any strategy with a paper-vs-real fill rate divergence > 15% as "not ready for promotion."
