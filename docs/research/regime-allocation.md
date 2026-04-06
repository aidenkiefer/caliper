# Regime Detection and Dynamic Capital Allocation for Polymarket and Crypto Strategies

## Problem framing and system constraints

A regime-aware allocation system exists to solve one core problem: **markets are non-stationary**, so “the best strategy” is usually conditional on prevailing conditions (volatility, liquidity, trend, event-time microstructure). Regime-switching time-series models were formalized decades ago for macro/financial dynamics and remain a standard way to represent discrete latent market states that change over time. citeturn0search0turn0search4

In crypto specifically, empirical work has found that volatility behavior can be better described by models that allow **multiple regimes** (including Markov-switching variants), consistent with the intuition that crypto alternates between calm and crisis states. citeturn1search7turn6search6

For prediction markets on entity["company","Polymarket","prediction market platform"], regime effects are amplified by **event-time structure** (time-to-expiry, settlement rules) and **CLOB microstructure**. Orders are expressed as limit orders, “market orders” are implemented as marketable limit orders, and maker-vs-taker decisions matter because taker fees exist on certain markets and fund maker incentives. citeturn2search3turn2search0turn2search1

The allocation system you want must therefore be:

- **Dual-scope:** detect **global regimes** (crypto-wide) and **local regimes** (per market, per hour, “time-to-close” windows).
- **Fee- and microstructure-aware:** Polymarket’s fee program explicitly funds a maker rebates program and runs liquidity rewards with market-level constraints like max spread/min size and daily distribution cadence. citeturn2search0turn2search1turn2search2
- **Robust to noise:** regime labels can be unstable; performance estimates are noisy; risk-adjusted metrics like Sharpe have estimation error and can be biased by serial correlation and sampling. citeturn0search14turn0search10
- **Safe under selection pressure:** once you have many strategies, comparing and reallocating among them becomes an “optimization over many trials,” where backtest overfitting and selection bias are well-studied failure modes. citeturn0search7turn0search3

## Regime definition framework

A “regime” should not be defined as a vague label (“bull/bear”). For production use, define regimes as a **small set of measurable state variables** over a specified horizon, then (optionally) map them into discrete labels. This makes the system inspectable and debuggable.

### Global regimes for crypto-wide conditions

A minimal, high-signal global crypto regime vector can be built from four families of features:

**Volatility**
- Realized volatility (RV) over multiple windows (e.g., 1h/6h/24h) and volatility-of-volatility. Regime-switching volatility models are specifically motivated by the empirical observation that volatility can jump between states. citeturn1search7turn0search0

**Liquidity proxies**
- Bid–ask spread, depth at best levels, volume, and “price impact sensitivity.” A robust microstructure finding is that price changes over short intervals are strongly related to **order flow imbalance**, with sensitivity inversely related to depth. citeturn3search1turn3search9

**Trend structure**
- Simple time-series momentum proxy: sign of trailing return, slope over lookback windows, and trend stability (fraction of positive returns). Trend-following evidence across long samples motivates treating persistent drift as a distinct state. citeturn4search11turn4search3

**Toxicity / adverse selection risk**
- If you have trade classification and volume imbalance, a common “toxicity” proxy is VPIN-style flow toxicity, designed to quantify conditions where liquidity provision is likely to be adversely selected by informed flow. citeturn6search0turn6search16

Output (global): a continuous vector \(G_t = [\text{RV}, \text{spread}, \text{depth}, \text{trend}, \text{toxicity}, ...]\), then map to regimes if needed.

### Local regimes for Polymarket hourlies and per-market conditions

Local regime design must incorporate “event-time,” not just price-time:

**Time-to-close and time-since-open**
- Polymarket hourly BTC contracts have a known resolution time, and the microstructure risk generally changes as resolution approaches (because information about the final payoff becomes progressively revealed by the underlying price path).

**Underlying reference dynamics**
- For hourly BTC markets, the settlement reference is an hourly BTC/USDT candle on entity["company","Binance","crypto exchange"]; the intrahour path is thus directly relevant for conditional probability estimation and for adverse selection near close. citeturn0file1

**Book state**
- Spread, depth, imbalance, and update intensity. Order flow imbalance and depth jointly predict short-term price impact in limit order markets, which is useful for local “toxicity” detection as the hour closes. citeturn3search9turn3search17

**Fee/incentive state**
- On Polymarket, taker fees fund maker rebates, and liquidity rewards depend on how orders sit relative to midpoint and market-specific spread/size thresholds (and are distributed daily). This makes “incentive regime” a real state variable, not an afterthought. citeturn2search0turn2search1turn2search2

**Operational state**
- Post-only orders and heartbeat/cancel logic create operational regimes: if a valid heartbeat is not received within the documented window, open orders are canceled. This affects both risk modeling and how “maker strategies” should be allocated under connectivity uncertainty. citeturn2search6turn2search3

Output (local): \(L_{m,t}\) for market \(m\), including time-to-expiry, microstructure state, and fee/incentive flags.

## Regime detection models and stability metrics

You want a detection layer that can produce either:
- a **hard regime label** \(z_t \in \{1,\dots,K\}\), or
- a **probability vector** \(p(z_t=k\mid x_t)\) that enables soft decisions and smoother allocations.

### Baseline: rule-based thresholds

This is the minimal viable baseline and is often the most stable:

- Define 2–4 states by thresholds on RV, spread, and trend (e.g., “high vol,” “low vol,” “trend,” “chop”).
- Add a distinct “near-close” state for hourly contracts (e.g., last 5–10 minutes), because adverse selection risk often rises when outcomes become more knowable. The market-making literature explicitly models dealers facing adverse selection and inventory risk in limit order books, motivating “state-aware” quoting and exposure control. citeturn3search0turn6search1

This baseline is essential because it becomes your **backstop** when HMM/clustering outputs are unstable.

### Hidden Markov Models and Markov-switching models

A canonical approach to discrete latent regimes is a Markov-switching model: an unobserved state evolves as a Markov chain and generates observed returns/volatility dynamics. The classic formulation is well-established, and modern variants are widely applied across financial time series. citeturn0search0turn0search4

For crypto volatility, research evaluating Markov-switching volatility models across large cross-sections of cryptocurrencies supports the practical relevance of multi-regime volatility dynamics. citeturn1search7turn6search6

Practical guidance:
- Use HMMs for regimes where you want clean probabilistic outputs and Markov-switching AR/GARCH variants when you specifically want regime-dependent mean/vol dynamics.
- Prefer **soft allocations** based on posterior regime probabilities to reduce whipsaw from regime flips.

### Bayesian regime switching

Bayesian approaches are valuable because they explicitly quantify uncertainty—especially when the evidence for switching is subtle. Bayesian tests and inference frameworks for Markov switching have been developed to address difficulties in classical testing. citeturn5search2turn5search6

Practical guidance:
- Bayesian switching is often best used when you want: (a) credible intervals on transition probabilities, (b) regularization via priors to prevent pathological transition matrices, and (c) more stable inference in small samples.

### Clustering: k-means, Gaussian mixture models, and t-mixtures

Unsupervised clustering is a pragmatic alternative: fit “states” as clusters in feature space (returns, vol, trend, liquidity). Mixture models are commonly proposed to model overlapping regimes and heavy-tailed behavior (t-mixtures can be more robust to outliers). citeturn5search4turn5search8turn5search5

Practical guidance:
- Use clustering as a **candidate regime generator**, then validate regimes by economic interpretability and stability (below).

### Stability and quality metrics for regimes

Regardless of method, score regimes with stability metrics so the allocator can penalize unreliable regime signals:

- **Switch rate:** number of regime changes per unit time.
- **Expected duration:** derived from transition probabilities in Markov regime models (a standard interpretability output). citeturn0search0turn0search4
- **Posterior entropy:** if the regime probability vector is diffuse, treat regime inference as uncertain and blend toward baseline allocation.
- **Cross-model agreement:** compare HMM vs clustering vs threshold baseline on the same period; unstable disagreement suggests regimes are not well-identified. citeturn5search19

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["Markov switching model regime diagram","Hidden Markov Model regime probabilities plot finance","risk parity portfolio allocation diagram","order flow imbalance depth bid ask diagram"],"num_per_query":1}

## Regime-conditioned strategy evaluation and the performance matrix

The allocator needs a strategy → regime mapping: “When regime \(k\) is active, what are the expected performance and risks of strategy \(s\)?”

### Regime-conditioned metrics

For each strategy \(s\) and regime \(k\):

- Expected return \(\mu_{s,k}\) (net of modeled fees/slippage).
- Volatility \(\sigma_{s,k}\) and downside risk (e.g., drawdown distribution).
- Tail risk proxies (e.g., expected shortfall or worst-case quantiles).
- Turnover and cost sensitivity.

You can compute these either:
- as hard-conditioned (use only periods assigned to regime k), or
- probability-weighted (weight each time point by \(p(z_t=k)\)).

### Why you must treat Sharpe and other ratios as uncertain estimates

Risk-adjusted statistics like Sharpe are estimated from finite noisy samples and can be distorted by serial correlation and sampling/aggregation effects. This is especially relevant when comparing fast strategies (hourly) and slow strategies (daily/weekly). citeturn0search14turn0search22

Because you will evaluate many strategies and variants, you should incorporate at least one “selection-bias-aware” safeguard when declaring a strategy “best in regime.” The literature provides explicit corrections/diagnostics for backtest overfitting and selection bias. citeturn0search7turn0search3

### Output: strategy → regime performance matrix

A useful production object is:

- \(M_{\mu}[s,k]\): expected net return
- \(M_{\Sigma}[s,k]\): covariance of strategies’ returns within regime \(k\)
- \(M_{\text{DD}}[s,k]\): drawdown stats
- \(M_{\text{cost}}[s,k]\): turnover/cost modes

This feeds directly into allocation.

## Allocation engine design with online adaptation and risk management

A production allocator should be **simple first, then extensible**. Below are allocation methods that scale from “solo developer” to “robust system” without requiring institutional complexity.

### Core architecture

Text diagram (module-level):

```text
Market Data + Features (global + local)
        |
Regime Detector  --->  Regime Probabilities p(z_t)
        |                          |
Strategy Performance Store   <---  Strategy Returns + Costs
        |
Allocator (regime-conditioned objectives + constraints)
        |
Risk Manager (hard/soft constraints)
        |
Execution Adapters (Polymarket, crypto venues)
        |
Ledger + Telemetry (PnL, exposures, fills, regime logs)
```

This structure aligns with the practical separation that execution is venue-specific, while strategy evaluation and allocation can be mostly market-agnostic (once costs and constraints are explicitly modeled). citeturn2search3turn4search0

### Allocation methods you can implement and compose

#### Risk parity / risk budgeting (robust baseline)

Risk parity allocates such that each component contributes a target share of portfolio risk (“risk budget”). This is often favored when expected returns are hard to estimate but risk metrics are more stable. citeturn1search0turn1search8

Implementation detail:
- If you treat each strategy as an “asset,” estimate the strategy return covariance (with shrinkage), then solve for weights that equalize risk contribution subject to constraints.

#### Hierarchical Risk Parity (HRP) for stability under estimation error

HRP is designed to address instability and concentration issues common in classical mean-variance optimization by using hierarchical clustering and recursive allocation. It is widely cited as a more stable alternative under noisy covariance estimates. citeturn1search2

Practical fit:
- HRP is attractive when you have a small number of strategies (4–20) and want robust diversification without fragile quadratic optimization.

#### Bounded fractional Kelly for sizing when you have calibrated edge estimates

Kelly-style sizing targets log-growth optimality but is sensitive to estimation error; fractional Kelly is commonly recommended for practicality and drawdown control. citeturn1search9turn1search1

Practical fit:
- Use “bounded Kelly” only for strategies with calibrated probability/edge estimates (e.g., Polymarket directional probabilities). Otherwise use risk-based sizing.

#### Mean–variance with shrinkage + turnover penalties (when you want return forecasts)

Mean–variance optimization is powerful but unstable if covariance matrices are poorly conditioned; shrinkage estimators improve conditioning and are widely used in practice. citeturn3search6turn3search14

To keep it realistic, incorporate transaction/turnover penalties:
- Portfolio optimization with linear transaction costs and turnover-type penalties is well-studied and can be formulated as convex optimization under common assumptions. citeturn4search0turn4search8

#### Bayesian allocation / Black–Litterman-style blending (for “views + uncertainty”)

Bayesian blending approaches provide a structured way to combine a prior (e.g., equilibrium/neutral weights) with uncertain strategy “views,” producing posterior expected returns and weights. This is the motivation behind Black–Litterman-style frameworks. citeturn4search2turn4search18

Practical fit:
- Combine your regime-conditioned expected returns as “views” with a neutral prior (equal weight or risk parity), scaling view confidence by regime posterior certainty and strategy track record.

### Online learning and adaptation

Your allocator needs to adapt without “chasing noise.” Two practical, research-backed design patterns:

**Discounted performance estimates**
- Use exponential forgetting factors to compute rolling \(\mu, \Sigma\) and to prevent obsolete periods from dominating allocations (especially across regime shifts).

**Expert-weighting / online portfolio selection**
- View each strategy as an “expert” and adjust weights based on recent performance under constraints; online portfolio selection surveys describe families of algorithms (follow-the-winner, follow-the-loser, meta-learning) that are designed for sequential decision contexts. citeturn3search3turn3search11

### Risk management layer

Hard constraints (always enforced):
- Max drawdown and kill-switch logic (system-level).
- Max exposure per market / per strategy.
- Inventory limits for maker strategies (especially relevant in CLOB market making, where inventory risk is a central modeled risk). citeturn3search0turn6search1

Soft constraints (trade-off controls):
- Volatility targeting to stabilize risk exposure (commonly used in systematic trend/risk parity contexts). citeturn1search0turn4search11
- Risk budgeting across strategy classes (directional vs maker vs event-driven).

**Polymarket-specific operational risk:** because the heartbeat mechanism can cancel open orders if not maintained, “connectivity uncertainty” should lower allocation to strategies that rely on continuous quoting unless redundancy is present. citeturn2search6

### Pseudocode for the unified allocation loop

```python
# Runs on a fixed cadence (e.g., every 30s or every 1m), plus event triggers near hour close.

def allocation_tick(t):
    # 1) Build global + local feature vectors
    G_t = global_features(t)                 # crypto-wide: vol/liquidity/trend/toxicity proxies
    L_t = local_features(t)                  # per-market: time-to-close, book state, fee flags, etc.

    # 2) Infer regime probabilities
    p_regime = regime_model.predict_proba(G_t, L_t)   # vector over K regimes
    regime_entropy = entropy(p_regime)

    # 3) Update strategy performance estimates (discounted)
    for s in strategies:
        perf_store.update(s, t, realized_return(s, t), costs(s, t))

    # 4) Compute regime-conditioned expectations
    mu, Sigma = perf_store.estimate_mu_sigma(p_regime, window="discounted")
    # optional: impose shrinkage for stability
    Sigma = shrink_covariance(Sigma)

    # 5) Compute candidate weights (choose method)
    w_raw = allocator.solve(
        method="hrp_or_risk_parity_or_mv",
        mu=mu,
        Sigma=Sigma,
        regime=p_regime,
        constraints=risk_constraints(),
        turnover_penalty=lambda_turnover,
    )

    # 6) Blend toward baseline under regime uncertainty
    w_base = baseline_weights()  # e.g., risk parity or equal-weight among "safe" strategies
    w = blend(w_raw, w_base, alpha=confidence_from_entropy(regime_entropy))

    # 7) Apply hard risk checks and market-specific caps
    w = risk_manager.enforce(w)

    # 8) Convert weights to target positions + generate orders via adapters
    orders = portfolio_to_orders(w, t, execution_state())

    # 9) Send orders and log allocation decision
    execution_router.submit(orders)
    telemetry.log_allocation(t, p_regime, w, mu, Sigma)
```

(The algorithmic choices above are grounded by regime-switching model frameworks, robust allocation approaches like risk parity/HRP, and online portfolio selection/meta-learning principles. citeturn0search0turn1search0turn1search2turn3search3turn3search6)

### Example allocation outputs over time (illustrative)

Assume four strategies: Polymarket MM, Polymarket Directional, Crypto Momentum, Cash. Example regimes: (R1) low-vol/trend, (R2) high-vol/chop, (R3) near-close toxic (hourly), (R4) connectivity degraded.

| Time window | Dominant regime | Example allocation weights |
|---|---|---|
| 10:00–10:30 | R1 | MM 0.35, Directional 0.30, Momentum 0.30, Cash 0.05 |
| 10:30–10:55 | R2 | MM 0.25, Directional 0.15, Momentum 0.20, Cash 0.40 |
| 10:55–11:00 | R3 | MM 0.10, Directional 0.10, Momentum 0.10, Cash 0.70 |
| Any time | R4 | MM 0.00, Directional 0.10, Momentum 0.10, Cash 0.80 |

The key behavior: the allocator reduces exposure under high entropy or high toxicity states, consistent with microstructure models emphasizing adverse selection risk for liquidity provision under informed flow. citeturn3search0turn6search0turn3search9

## Backtesting and evaluation methodology

A regime-aware allocator must be tested in a way that does not “cheat” by using regime-conditioned performance in-sample.

### Baselines and comparisons

You need two orthogonal baselines:

- **Static allocator:** fixed weights (equal weight, fixed risk parity).
- **Regime-agnostic dynamic allocator:** adapts based on performance but ignores regime labels.

Then evaluate:
- static vs dynamic
- regime-aware vs regime-agnostic

This isolates whether regimes add incremental value rather than just “adaptive weighting.”

### Walk-forward and regime transition stress tests

Walk-forward evaluation is essential for non-stationary systems, because a regime model can look great in-sample and fail out-of-sample when transition dynamics change. citeturn6search7

Add explicit stress tests:
- Evaluate performance during and immediately after regime transitions (e.g., volatility shock onset).
- Measure “regime flip sensitivity” (how much allocation changes per unit time) and whether turnover costs erase benefits.

### Selection-bias and overfitting controls

Because you will iterate on strategies and allocator settings, treat allocator tuning as a multiple-testing process. Use at least one of:

- **Deflated Sharpe Ratio / selection-bias-aware evaluation** for strategy/allocator comparisons. citeturn0search7
- **Probability of Backtest Overfitting (PBO)** style diagnostics to estimate how likely your “best” configuration is selected by chance. citeturn0search3
- **Probabilistic Sharpe Ratio (PSR)** (or equivalent) to convert observed Sharpe into a credibility probability and a minimum track record length threshold. citeturn5search3turn5search7

### Execution realism and turnover penalties

Even if execution is simulated, incorporate transaction cost realism:

- Use explicit turnover penalties and cost models; convex formulations with linear transaction costs are well-studied and tractable. citeturn4search0turn4search8
- For strategies sensitive to execution timing (market making, near-close behavior), consider incorporating execution risk concepts from optimal execution literature (trade-off between cost and risk over time). citeturn4search1

### Polymarket-specific evaluation requirements

Because Polymarket has:
- limit-order mechanics (market orders are marketable limit orders), citeturn2search3
- maker rebates funded by taker fees, citeturn2search0turn2search1
- liquidity rewards with market-specific constraints and daily distribution cadence, citeturn2search2turn2search5
- and heartbeat-driven order cancellation risk, citeturn2search6

your backtests and paper simulations should log PnL decomposition into:
- spread capture
- inventory drift/adverse selection
- fees paid (taker)
- incentives earned (maker rebates, liquidity rewards)

Without decomposition, allocators can unknowingly “optimize toward incentive noise” or underprice adverse selection.

