# Cross-Sectional Opportunity Ranking and Market Selection

We need a system to scan all available markets (Polymarket BTC hourly windows, other event contracts, crypto pairs) and **rank them by tradable edge** and execution quality. The goal is to use our Polymarket probability model and fee/slippage estimates to pick the best trades across markets, dynamically. Key steps:

1. **Universe Definition:** Which markets to consider, with liquidity and spread filters.  
2. **Edge Estimation (Mispricing):** Compute predicted vs implied probabilities, net of costs.  
3. **Execution Feasibility:** Score each market’s tradeability (book depth, spread, queue).  
4. **Ranking Function:** Combine expected value, risk, liquidity, confidence into a score.  
5. **Selection Logic:** Choose top-ranked markets subject to diversification.  
6. **Temporal Dynamics:** Handle entry/exit timing, ranking refresh rate.  
7. **Backtesting:** Compare multi-market ranking vs single-market baseline, measure return distribution and hit rate.

All components must **integrate with the existing Polymarket probability model** and the fee/slippage models, and handle fast-moving, low-liquidity markets.

---

## 1. Universe Definition

We must decide which markets to include in the ranking. For a Polymarket-focused system:

- **Hourly BTC markets:** By default, include *all* active Polymarket BTC hourly contracts (every open hour). These have identical structures.  
- **Multi-timeframe:** Optionally include 5-minute or 15-minute BTC contracts if available (shorter horizons increase signal updates but also noise).  
- **Other prediction markets (optional):** E.g. binary yes/no markets on elections or events. These can be added later if reliable probability models exist.

For each candidate market, apply **liquidity filters** to avoid illiquidity traps:
- **Volume filter:** Exclude markets with negligible recent trading volume. For example, skip markets averaging less than X USDC traded per hour.  
- **Depth filter:** Exclude markets with very low order book depth (tiny aggregate available at near-the-money levels). Shallow markets would incur high slippage for any meaningful trade.  

Also enforce **spread constraints**: If the best bid–ask spread is too large (relative to 100% range), the execution cost likely outweighs any expected edge. A practical rule is to skip markets where spread > Y% of price (e.g. >1–2 percentage points on binary market).

*(No citation required: this filtering logic is standard practice in cross-sectional trading systems.)*

---

## 2. Edge Estimation per Market

For each market \(m\) at time \(t\), we compute a **mispricing measure** \(M_{m,t}\):

1. **Model probability \(\hat p_{m,t}\).** Use our trained Polymarket probability model (e.g., logistic forecast from features) to predict the probability that “YES” resolves. This could incorporate order flow, external signals, etc.  
2. **Implied probability \(p_{m,t}\).** Convert the current market mid-price into a probability: e.g. for a YES contract at price 47.5, \(p=0.475\).  
3. **Raw mispricing \(M = \hat p - p\).** This is the expected edge. A positive \(M\) means model thinks the contract is undervalued (buy YES), negative means overvalued (buy NO).  

We must **adjust \(M\) for costs and execution factors**:

- **Fees:** Polymarket charges taker fees (0.45–1.80% depending on price) and gives maker rebates (10% of taker fees). Net expected value must subtract the fee that our trade will incur. ([docs.polymarket.com](https://docs.polymarket.com/trading/fees?utm_source=chatgpt.com))  
- **Spread and slippage:** Instead of assuming immediate execution at midpoint, incorporate expected slippage. For example, if spread is 0.4 points, assume filling at mid ± half spread.  
- **Latency decay:** In fast markets, our stale signals degrade. We can model a latency penalty by slightly diminishing \(\hat p\) based on how old it is or how fast the market moves. 

The **net expected value (EV)** can be approximated as:
\[
\text{EV}_{m,t} \approx (\hat p_{m,t} - p_{m,t}) \cdot \text{payout} - \text{costs}_{m,t},
\]
where “costs” includes the fee and half-spread. If betting $1, payout is $1, then EV = \(\hat p - p\) minus fee.\

*(The idea of adjusting edge for fees and slippage is common in trading systems. For example, standard ML traders subtract transaction costs from model-based edge【11†L8-L12】【11†L14-L15】.)*

---

## 3. Execution Feasibility Scoring

Even if a market has a high raw EV, it may be impractical to trade. We assign each market a **feasibility score** based on liquidity:

- **Order book depth:** How much size is available within a few ticks of the midpoint. Deeper orders mean we can execute larger trades with less price impact. Cont *et al.* show that order flow impact is inversely related to depth【11†L8-L12】.  
- **Spread width:** Narrow spreads indicate tight pricing; wide spreads directly reduce edge.  
- **Fill probability:** Estimate how likely a limit order would fill (if we use limit orders). A simple proxy is “queue position”: if many orders are ahead, a post-only order likely won’t execute immediately, forcing either higher slippage or timed risk.  
- **Activity rate:** How frequently trades occur (implied by candle updates or order event rate). Rapid trading suggests we can get fills quickly.

Combine these into a single **liquidity metric** (for example, normalized depth divided by volatility). Then define a *“slippage factor”* \(\lambda_{m,t}\in[0,1]\) that shrinks EV by expected execution cost:
\[
\text{EV}_{m,t}^{\text{adj}} = \text{EV}_{m,t} \times \lambda_{m,t}.
\]
A simple approach is \(\lambda = \exp(-\alpha\,\text{spread}/\sigma)\), with \(\alpha\) calibrated on historical fills (larger spreads relative to volatility give lower \(\lambda\)). More robustly, \(\lambda\) can come from simulated limit order backtests: e.g. what fraction of arbitrage would have been captured with a realistic fill rate.

No single paper gives this formula, but the **principle** is standard: rank opportunities by *realistic* edge, not theoretical edge. (Related work on limit order execution emphasizes modeling fill rates and slippage [Cont *et al.* 2014【13†L1-L4】] and adjusting signals accordingly.)

---

## 4. Ranking Function

We now need a unified **score** for each market combining multiple dimensions. A generic form is:
\[
\text{Score}_m = w_{EV} \cdot \text{EV}^{\text{adj}}_{m}
+ w_{R} \cdot \frac{\text{EV}^{\text{adj}}_{m}}{\sigma_{m}}
+ w_{L} \cdot \text{LiquidityScore}_{m}
+ w_{C} \cdot \text{Confidence}_{m},
\]
where:
- \(\text{EV}^{\text{adj}}_m\) is the expected value after adjustments.  
- \(\frac{\text{EV}^{\text{adj}}_m}{\sigma_m}\) is a risk-adjusted term (Sharpe-like) using estimated outcome volatility \(\sigma_m\).  
- \(\text{LiquidityScore}_m\) measures ease of execution (higher for tighter spreads, more depth).  
- \(\text{Confidence}_m\) is the probability model’s confidence or edge reliability (e.g., p̂(1-p̂) or Brier score).  

The weights \(w\) can be tuned or set to equal for a simple linear score. A well-known form in trading is **Information Ratio** style (EV/vol) plus *certainty-weighting*. For example, the score might be:
\[
\text{Score}_m \;=\; \frac{\text{EV}^{\text{adj}}_{m}}{\sigma_m + \epsilon} \;\times\; \text{LiquidityWeight}_m \;\times\; (1 - 2|p_{m}-0.5|),
\]
so that high Sharpe * high liquidity * high-probability markets rank higher. (This is analogous to the “consensus signal” idea in ensemble models【10†L14-L18】 but here realized via book liquidity.)

**Justification:** This multi-factor ranking reflects best practices in quant selection: it rewards high alpha-per-risk while penalizing illiquidity and low confidence. In equities, similar multi-metric scores (momentum * quality * liquidity) are common【turn1search15†L0-L10】. Here we adapt to Polymarket specifics by weighting probability spread and execution.

In practice, one might also cap the score to positive values and treat negative EV markets as zero (no trade). 

---

## 5. Portfolio Selection Logic

Once all markets are scored, we select a subset to trade:

- **Top-N or threshold:** A simple rule is “take the top \(N\)” markets by score (e.g. the 3 highest). Alternatively, include all markets with score above a cutoff.  
- **Capital allocation:** Split capital among selected markets. At minimum, equal-weight them (or weight by their score). More sophisticated: apply a **risk-parity** or **Kelly/mean-variance** allocator across the chosen markets (treating each market as an “asset”).  

To avoid concentration, enforce **diversification constraints**:
- **Correlation penalty:** If two top markets are almost identical (e.g. overlapping time windows, or two sides of the same binary contract), you might skip one. For instance, skip selecting both YES and NO sides of the same market.  
- **Category limits:** Avoid picking all from a single category if others are also promising (for portfolio robustness).  
- **Maximum weight:** Limit any single market’s capital fraction (e.g. <50%).

*(These are standard portfolio safeguards: e.g. constructing equal/sector-weighted portfolios to avoid cluster risk【10†L14-L18】【aqr.com】.)*

Pseudo-code example:

```python
scores = {m: compute_score(m) for m in all_markets}
selected = sorted(scores, key=scores.get, reverse=True)[:N]  # top N
# Alternatively: [m for m in all_markets if scores[m] > threshold]
w = allocate_weights(selected, method="equal" or "risk_parity")
w = enforce_diversification(w, max_per_pair=0.5)
```

The result is a weight or bet size per chosen market, ready for order generation.

---

## 6. Time Dynamics and Re-ranking

Markets can move in and out of favor quickly, so we must update the ranking and portfolio periodically:

- **Re-ranking frequency:** For hourly BTC markets, a natural cadence is every minute or on significant events (new order, trade). Too-frequent re-ranking invites overtrading; too-infrequent misses opportunities. Empirically, a 1–5 minute rhythm is reasonable for intraday/high-frequency strategies.  

- **Entry/exit rules:** When a market enters the top-N, generate new orders. When it drops out (score falls), decide whether to unwind (if already in position) or ignore. A cooldown can prevent flip-flopping: e.g., require a market to remain below top-N for \(k\) periods before exiting.  

- **Stability of top opportunities:** Track how scores change over time. If certain markets (e.g. particular hours) repeatedly appear at the top, they may warrant special focus or permanent inclusion. If a market oscillates around the cutoff, consider it “borderline” and handle its orders more conservatively (smaller size, protect profit).  

All these dynamics should be logged and backtested to avoid “thrashing.” Frequent re-ranking should be accompanied by turnover penalties in the allocation (as in Section 4) to avoid excessive trading costs【web.stanford.edu】.

---

## 7. Backtesting Framework and Evaluation

We must test the ranking strategy vs baselines:

- **Compare to single-market strategy:** E.g., only trading the current hour’s BTC market using the same directional model. The ranking approach should improve metrics like cumulative return or Sharpe, or at least Capital Efficiency (higher return per unit volume traded).  
- **Metrics:** Use return distribution (mean, volatility), Sharpe ratio, hit rate (fraction of positive P&L trades), and capital efficiency (return per trade or per volume). Also track maximum drawdown and tail risk.  

- **Hit rate vs edge:** Because we select by predicted edge, record the realized edge (profit) for each top market when traded. A high hit rate with good average return indicates the ranking was effective.  

- **Statistical validation:** Use walk-forward splits to avoid look-ahead. One approach: train/validate the probability model and ranking parameters on one segment, then simulate on the next (rolling window). This guards against overfitting and regime-specific tuning.  

- **Sensitivity tests:** Stress-test the ranking by simulating delays and incomplete fills (e.g., assume only 80% of predicted EV is realized due to slippage). Check if the strategy still beats baselines. Also test “feature ablation”: how much does the strategy rely on each component of the score?  

*(No single reference covers this whole framework, but the idea is consistent with standard backtest best practices in quant trading【davidhbailey.com†L1-L4】【ssc.wisc.edu†L1-L5】.)*

---

## Integration Plan

- **Ranking formula:** Final score formula (chosen from above) documented in code.  
- **Pipeline pseudocode:** See snippets above; implement as a standalone service or as part of the strategy ensemble.  
- **Example output:** A sample might look like:

   | Market        | Score | Adj. EV | Liquidity | Weight |
   |---------------|-------|---------|-----------|--------|
   | BTC 14:00 YES | 0.85  | +1.2%   | High      | 0.30   |
   | BTC 15:00 NO  | 0.72  | +0.8%   | Medium    | 0.25   |
   | BTC 13:00 YES | 0.65  | +1.0%   | Low       | 0.20   |
   | BTC 16:00 NO  | 0.60  | +0.5%   | High      | 0.25   |

  *(Higher score = higher priority. The table is illustrative; actual scores come from the formula.)*

- **Allocation integration:** The selected markets and their weights feed directly into the system’s **portfolio allocator** (see “Regime Detection” plan) as “assets.” The ranker’s chosen weights become one input to the global allocation engine.  

In summary, this ranking system continuously identifies the most promising markets given our predictive model and execution costs, so that capital is deployed where it is most likely to yield positive EV. With rigorous backtesting and safeguards, it will significantly enhance the platform’s ability to capture cross-market opportunities.

