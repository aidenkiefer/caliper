# Reward-Density Game Analysis for Polymarket Hourly BTC Markets

## Executive summary

This report frames *rewards + maker rebates* on Polymarket as a repeated competitive game among liquidity providers (“makers”), then outlines a concrete methodology to identify hourly BTC “Up/Down” windows with the best **reward density** per unit of **competition** and **risk**, using Polymarket’s public docs/APIs and (where live programmatic pulls aren’t feasible) calibrated parameter ranges. citeturn27search1

Key conclusions:

Polymarket’s incentive stack for hourly BTC markets is dominated (in most realistic cases) by **maker rebates funded by taker fees**—because these rebates scale with *actual trading volume* and the *fee curve* that peaks near 50/50 implied probability. citeturn21search0turn24view0

For crypto markets, the **current (pre–Mar 30, 2026) fee curve** uses `feeRate=0.25` and `exponent=2` (peak effective rate ≈ **1.56%** near p=0.5), and crypto maker rebates are **20%** of the taker-fee pool. citeturn24view0turn21search0

An **upcoming fee expansion/update** takes effect **March 30, 2026**. For **Crypto**, parameters become `feeRate=0.072`, `exponent=1` with a **peak effective rate ≈ 1.80%**, with **20%** maker rebate; this meaningfully increases maker-rebate “reward pools” *especially in markets that drift away from 50/50* because the exponent drops from 2→1. citeturn24view0

Liquidity rewards (the “Daily Rewards” system) are a separate subsidy mechanism with market-level constraints like **max spread** and **min size**, and a scored allocation rule; they can dominate in some low-competition markets, but you must treat **reward pool sizes** and **eligibility** as market-specific inputs fetched from the rewards endpoints or UI. citeturn0search8turn0search15turn10search0

Using a small but concrete March 24–25, 2026 sample of hourly BTC windows (with Polymarket-reported volumes), the windows with large traded volume produced orders-of-magnitude larger estimated maker-rebate pools than adjacent “dead” windows—implying that *if* you can manage adverse selection, the best reward-density opportunities typically cluster where taker flow exists. citeturn32view2turn33view0turn34view0turn34view1turn34view2turn32view0

## Incentives and rule primitives you must model

### Taker fees and maker rebates as a volume-driven contest

Polymarket’s fee-enabled markets charge a **taker fee** computed (in USDC terms) as:  
\[
\text{fee} = C \times p \times \text{feeRate} \times \big(p(1-p)\big)^{\text{exponent}}
\]  
where \(C\) is shares traded and \(p\) is the share price (interpretable as implied probability). citeturn24view0

For each eligible market, a portion of fees becomes the **maker rebate pool**, and a maker’s share is proportional to a per-fill “fee-equivalent” quantity using the same curve:  
\[
\text{fee\_equivalent} = C \times p \times \text{feeRate} \times \big(p(1-p)\big)^{\text{exponent}}
\]
\[
\text{rebate} = \frac{\text{your\_fee\_equivalent}}{\text{total\_fee\_equivalent}} \times \text{rebate\_pool}
\]  
and “totals are calculated per market,” meaning you compete only with other makers in that same market. citeturn21search0

For hourly BTC markets specifically, the maker rebate program explicitly covers “**1H, 4H, Daily, Weekly Crypto**” starting **Mar 6, 2026+**, at **20%** maker rebate (fee-curve weighted). citeturn21search0turn21search6

### The March 30, 2026 fee regime change

Polymarket’s “Fees” doc provides both:

Current fee structure (live as of Mar 25, 2026): Crypto `feeRate=0.25`, `exponent=2`, maker rebate 20%, peak effective rate ≈ 1.56%. citeturn24view0

Upcoming fee structure effective **March 30, 2026**: Crypto `feeRate=0.072`, `exponent=1`, maker rebate 20%, peak effective rate ≈ 1.80%, plus expansion to additional categories (with geopolitics explicitly fee-free). citeturn24view0

For hourly BTC markets, this implies the *expected incentive pool per unit of volume* increases (from ~0.3125% of notional at p≈0.5 to ~0.36% at p≈0.5), and the pool becomes less concentrated around p≈0.5 because exponent decreases from 2→1. citeturn24view0

### Liquidity rewards as a separate scored subsidy with constraints

Liquidity rewards are described as:

A system to “reward liquidity providers,” with rewards distributed directly to maker addresses daily (midnight UTC), and with an option for **sponsored rewards** where sponsors deposit USDC into a smart contract that distributes rewards to LPs in that market. citeturn0search15

A score-based mechanism where (at a high level) an order’s contribution depends on (i) size, (ii) closeness to midpoint, and (iii) price-level desirability, and then rewards are allocated based on share of score. citeturn0search8turn0search15

Operationally, reward-eligible markets expose config fields such as **`rewards_max_spread`** and **`rewards_min_size`** through rewards endpoints (used by the Daily Rewards UI and API consumers). citeturn10search0

A critical implementation detail: Polymarket provides an **order scoring status** check (to verify whether your resting orders are currently scoring), and scoring also depends on the order being “live for the required duration,” i.e., an on-book time requirement. citeturn5search18turn15search18

Because reward pool sizes, max spread, and min size are market-specific and can change, this report models them as **parameters** unless fetched live from rewards endpoints/UI at run-time. citeturn10search0turn0search15

### Market microstructure constraints that affect competitive dynamics

Polymarket uses a CLOB; “prices are probabilities” in \([0, 1]\) and the displayed price is generally the midpoint of the bid-ask spread (subject to UI rules when spreads are very wide). citeturn21search5

Order lifecycle is hybrid: orders are created offchain, matched by an operator, and settled onchain through smart contracts. citeturn36search2turn35search5

Post-only orders (maker-only) are supported; if they would cross the spread, they are rejected instead of executed. citeturn36search0turn36search1

A bot must implement resiliency around infrastructure mechanisms:
- **Weekly matching engine restart**: Mondays at 20:00 ET, typically ~90 seconds, with order endpoints returning HTTP **425**; clients should back off and retry. citeturn35search0turn35search1  
- **Rate limits** enforced via entity["company","Cloudflare","edge services company"] throttling; over-limit requests are delayed/queued rather than immediately rejected, and per-endpoint limits differ across Gamma/Data/CLOB APIs. citeturn27search7  
- **Heartbeat safety**: if a valid heartbeat is not received within 10 seconds (plus buffer), all open orders are cancelled; this strongly shapes “always-on” market-making bot design. citeturn36search0turn36search3

## Prioritized data sources and exact endpoints to fetch

Polymarket exposes three major public APIs (Gamma, Data, CLOB), plus rewards and rebates endpoints on the CLOB host; public endpoints generally do not require authentication, while trading endpoints do. citeturn27search1turn27search10

### Table of prioritized endpoints and required fields

| Priority | Source | Endpoint | What to fetch (fields) | Why it matters for reward density |
|---:|---|---|---|---|
| 1 | Polymarket CLOB | Rewards markets listing (multi) | `condition_id`, `price`, `volume_24hr`, `rewards_min_size`, `rewards_max_spread`, `rewards_config.rate_per_day`, `market_competitiveness` | Direct inputs for liquidity-reward pool size and constraints; competitiveness proxy if available. citeturn10search0 |
| 1 | Polymarket CLOB | Rewards markets current | List of reward configs by market + eligibility flags | Needed to detect which hourly BTC windows are actually rewarded (and under what constraints). citeturn1view2 |
| 1 | Polymarket Docs | Fee schedule (current + upcoming) | Crypto `feeRate`, `exponent`, maker rebate %; effective dates | Governs taker-fee pool and maker-rebate pool per unit volume, especially post–Mar 30. citeturn24view0turn21search0 |
| 1 | Polymarket CLOB | Fee rate check | `GET /fee-rate?token_id={token_id}` → `base_fee` | Detect fee-enabled markets programmatically (don’t hardcode). citeturn22search8turn24view0 |
| 1 | Polymarket CLOB | Rebates (maker) | `GET /rebates/current?date=YYYY-MM-DD&maker_address=…` | Ground truth of realized rebated fees per maker/market/day (for backtesting & calibration). citeturn21search1 |
| 1 | Polymarket CLOB | Order scoring status | `GET /order-scoring` for order IDs | Verifies if your order is scoring (liquidity rewards / scoring eligibility). citeturn5search18turn15search18 |
| 1 | Polymarket Gamma | Markets/events discovery | `GET /markets`, `GET /events` (with filters) | Locate the exact hourly BTC windows (condition IDs, token IDs, metadata). citeturn27search1turn27search10 |
| 1 | Polymarket Data API | Trades | `GET https://data-api.polymarket.com/trades` → `conditionId`, `side`, `size`, `price`, `timestamp`, `transactionHash` | Builds realized flow, last-minute toxicity proxy, and volume confirmation by time bucket. citeturn27search0 |
| 2 | Polymarket Data API | Leaderboard | `GET /v1/leaderboard` → `proxyWallet`, `vol`, `pnl` | Approximate “who is big” and infer competition regimes / concentration. citeturn27search11 |
| 2 | Polymarket on-chain | OrderFilled logs on entity["organization","Polygon","blockchain network"] | From CTF Exchange `OrderFilled`: `maker`, `taker`, `fee`, `makerAssetId`, `takerAssetId`, amounts | Best source to estimate maker concentration (HHI), effective # makers, and fee-equivalent share. citeturn26search0turn26search1turn26search3 |
| 2 | Binance spot | `GET /api/v3/klines` | For symbol `BTCUSDT`, interval `1h`, OHLCV arrays | Risk metric foundation: realized volatility, trend, hour-close dynamics. citeturn28search0turn28search3 |

### Minimal API/repo link bundle (pasteable)

```text
# Polymarket API base URLs (official)
https://docs.polymarket.com/api-reference
https://gamma-api.polymarket.com
https://data-api.polymarket.com
https://clob.polymarket.com

# Polymarket fee schedule (current + March 30 update)
https://docs.polymarket.com/trading/fees

# Maker rebates program (rules + formula)
https://docs.polymarket.com/market-makers/maker-rebates

# Liquidity rewards program (rules + scoring)
https://docs.polymarket.com/market-makers/liquidity-rewards
https://help.polymarket.com/en/articles/13364463-liquidity-rewards-program

# Rewards endpoints (API reference)
https://docs.polymarket.com/api-reference/market-data/get-multiple-markets-with-rewards
https://docs.polymarket.com/api-reference/market-data/get-current-markets-with-rewards
https://docs.polymarket.com/api-reference/order/verify-if-an-order-is-scoring

# Rebates + fee-rate endpoints
https://docs.polymarket.com/api-reference/rebates/get-current-rebated-fees-for-a-maker
https://docs.polymarket.com/api-reference/market-data/get-fee-rate

# CLOB official clients (mentioned in fees doc)
TypeScript: @polymarket/clob-client
Python: py-clob-client
Rust: polymarket-client-sdk

# Binance spot klines (1h candles)
https://api.binance.com/api/v3/klines
```

## Methodology: define reward density, competition, and risk

### Precise objective

For each hourly BTC “Up/Down” market window \(i\), estimate a **ranking score** for expected net returns from incentives (maker rebates + liquidity rewards), normalized by **competition** and **risk**:

\[
\text{Score}_i
= \frac{\mathbb{E}[\text{Incentives}_i]}{\text{Competition}_i^{\alpha}\;\text{Risk}_i^{\beta}}
\]

This is explicitly *not* total PnL (which requires spread-capture, inventory drift, and adverse selection modeling). Instead, this isolates the “reward density” component that many bot builders target first. Maker rebates are awarded per market based on fee-equivalent share, so windows are independent games (“you only compete with other makers in the same market”). citeturn21search0

### Incentives decomposition

Define hourly incentives as:

\[
\mathbb{E}[\text{Incentives}_i]
=
\underbrace{\mathbb{E}[\text{MakerRebatePool}_i] \cdot \mathbb{E}[s_i]}_{\text{maker rebates}}
+
\underbrace{\mathbb{E}[\text{LiquidityRewardPool}_i] \cdot \mathbb{E}[\ell_i]}_{\text{liquidity rewards}}
\]

Where:

MakerRebatePool\(_i\) is a function of taker-fee pool (volume × effective fee rate) and maker rebate %. citeturn24view0turn21search0

\(s_i\) is your expected share of fee-equivalent in that market’s fills (requires estimating your queue priority and your fraction of executed maker liquidity). citeturn21search0turn35search6

LiquidityRewardPool\(_i\) derives from rewards config like `rate_per_day` (convert to per-hour when applicable), plus sponsored rewards if any; your share \(\ell_i\) depends on scoring (size, price, closeness to midpoint) and on satisfying constraints (`rewards_max_spread`, `rewards_min_size`, and “required duration” on-book). citeturn0search8turn0search15turn10search0turn15search18

### Competition metric

A robust (and implementable) competition metric should track the **effective number of makers** competing for the pool, not merely raw liquidity:

From on-chain OrderFilled events (maker addresses), compute maker fee-equivalent shares \(w_{i,k}\) for maker \(k\) in market \(i\) over a lookback window (e.g., last 7 days for that hour-of-day). Onchain OrderFilled provides `maker` and `fee` fields you can use to aggregate. citeturn26search1turn26search3turn26search0

Define concentration via Herfindahl-Hirschman Index (HHI):

\[
\text{HHI}_i = \sum_k w_{i,k}^2
\quad\Rightarrow\quad
N^{\text{eff}}_i = \frac{1}{\text{HHI}_i}
\]

Use \(N^{\text{eff}}_i\) as your **Competition\(_i\)**, optionally blended with orderbook tightness and depth.

If you cannot compute on-chain maker shares yet, the rewards endpoint exposes a `market_competitiveness` field you can use as a first proxy (treat it as an externally defined competitiveness index). citeturn10search0

### Risk metric tailored to hourly BTC windows

Define risk as adverse selection exposure + inventory uncertainty:

Use Binance 1h BTCUSDT klines for each window:
- Realized volatility \(\sigma_i\) from intrahour returns (or high/low range if you stay at 1h candles).
- Trend-to-close: \(|\text{Close}-\text{Open}|/\text{Open}\), because the hour’s directional move often correlates with informed flow near close.
Binance exposes 1h kline data via `/api/v3/klines` with `interval=1h`. citeturn28search0turn28search3

From Polymarket trade history (Data API), compute a last-minute toxicity proxy:
- Volume share in last 5 minutes of the window vs earlier minutes.
- Aggressor side imbalance (BUY vs SELL). citeturn27search0

A simple composite:

\[
\text{Risk}_i = z(\sigma_i) + \lambda \cdot z(\text{Toxicity}_i)
\]

## Step-by-step algorithm and pipeline

### Data processing rules

Time alignment:
- Use the window definition embedded in each hourly market’s rules: resolution depends on the BTC/USDT 1-hour candle beginning at the specific time in the title, with open/close on Binance. citeturn32view2turn32view0  
- Align all timestamps to ET for the market window and convert to UTC for API queries.

Handle missing reward pool sizes:
- If `rate_per_day` / sponsored pool sizes are not available (or the market is not present in rewards listings), treat liquidity rewards as a parameter range \([0, R^{\max}]\) and run sensitivity. citeturn0search15turn10search0

### Pseudocode for ranking hourly windows

```text
INPUTS:
  - Lookback horizon H days (e.g., 14 or 30)
  - Candidate hourly BTC markets i (condition_id, token_ids) from Gamma
  - Fee regime (current vs post-Mar-30)
  - Maker rebate % (crypto = 20%)
  - Liquidity rewards config per market (if any): max_spread, min_size, rate_per_day, sponsored pools
  - Parameters: alpha (competition penalty), beta (risk penalty)

FOR each market window i:
  1) Fetch Polymarket market metadata via Gamma:
       - condition_id, token_ids, start/end timestamps, tags/category
  2) Compute realized market volume V_i over the window (or from market page / Data API).
  3) Estimate taker-fee pool:
       - Estimate E[effective_fee_rate_i] using trade-price distribution p_t (from Polymarket trades)
       - fee_pool_i = V_i * E[effective_fee_rate_i]
  4) Maker rebate pool:
       - rebate_pool_i = maker_rebate_pct * fee_pool_i
  5) Estimate competition:
       - From on-chain OrderFilled logs:
           * compute maker fee-equivalent shares w_{i,k}
           * HHI_i = sum_k w_{i,k}^2
           * Neff_i = 1 / HHI_i
       - If missing, use rewards API market_competitiveness proxy.
  6) Estimate risk:
       - From Binance 1h klines: sigma_i, |close-open|
       - From Polymarket trades: last-5-min volume share, imbalance
       - Risk_i = z(sigma_i) + lambda * z(toxicity_i)
  7) Estimate liquidity reward expected share (if rewards enabled):
       - Use rewards_max_spread, rewards_min_size, scoring spec
       - Approximate expected scoring share from your planned quoting policy and Neff_i
  8) Score:
       - ExpectedIncentives_i = rebate_pool_i * E[s_i] + liquidity_reward_pool_i * E[l_i]
       - Score_i = ExpectedIncentives_i / (Competition_i^alpha * Risk_i^beta)

OUTPUT:
  - Ranked list of windows by Score_i
  - Sensitivity sweeps over alpha, beta, reward_pool assumptions, minimum on-book time
```

### Mermaid flowchart of the pipeline

```mermaid
flowchart TD
  A[Gamma API: discover hourly BTC markets\ncondition_id, token_ids, schedule] --> B[Ingest Polymarket trades\nData API /trades]
  A --> C[Ingest orderbooks\nCLOB /book + /midpoint]
  A --> D[Fetch rewards config\nCLOB rewards endpoints\nmax_spread, min_size, rate_per_day]
  A --> E[Fetch fee regime\nFees doc + /fee-rate]
  B --> F[Compute volume + price-path p(t)\nlast-5-min toxicity]
  E --> G[Compute taker-fee pool + maker rebate pool]
  H[On-chain OrderFilled\nmaker/taker/fee\nPolygon] --> I[Compute maker concentration\nHHI, Neff]
  J[Binance klines 1h\nvolatility + trend] --> K[Risk score]
  D --> L[Liquidity rewards pool estimate\nand scoring eligibility]
  F --> M[Competition proxy fallback\nif on-chain incomplete]
  G --> N[Incentive expectation]
  I --> O[Competition metric]
  K --> P[Risk metric]
  L --> N
  M --> O
  N --> Q[Reward density score\nScore_i]
  O --> Q
  P --> Q
  Q --> R[Rank windows\n+ sensitivity analysis]
```

## Illustrative ranking of hourly BTC windows using March 2026 snapshots

### Observed market volumes (ground truth sample)

The following hourly BTC windows show sharply different realized volumes even within the same day. For example, on March 25, 2026:
- 8–9AM ET: **$242,384** volume citeturn33view0  
- 9–10AM ET: **$1,926** volume citeturn34view0  
- 10–11AM ET: **$61** volume citeturn34view1  
- 11AM–12PM ET: **$61** volume citeturn34view2  
- 3–4PM ET: **$45** volume citeturn32view0  

And on March 24, 2026:
- 4–5PM ET: **$181,970** volume citeturn32view2  

All these hourly markets resolve based on whether the BTC/USDT 1-hour candle close on Binance is ≥ its open for the hour stated in the title. citeturn32view2turn32view0

### Table of top candidate windows by estimated maker-rebate reward density

Assumptions for the computed columns (explicit):
- Fee regime: **current** (pre–Mar 30) unless stated; crypto: `feeRate=0.25`, `exponent=2`, maker rebate 20%. citeturn24view0turn21search0  
- Average effective fee rate approximated at the **p=0.5 peak** (i.e., 1.56% current, 1.80% post–Mar 30). This is a *stress-test / upper-bound* assumption; real averages can be lower if prices spend time near extremes. citeturn24view0  
- Liquidity rewards fields (**max_spread**, **min_size**) are market-specific and must be fetched from rewards endpoints; if absent, treat as “not reward-enabled.” citeturn10search0turn0search15  
- Competition and concentration are illustrative proxies (calibrated ranges) pending on-chain maker-share measurement via OrderFilled events. citeturn26search1turn26search3turn26search0  

| Candidate hourly BTC window (ET) | Observed volume (USD) | Est. maker-rebate pool (current, p≈0.5) | Est. maker-rebate pool (post–Mar 30, p≈0.5) | Est. effective makers \(N^{eff}\) (proxy) | Est. competitor concentration (HHI range, proxy) | Est. per-maker rebate (current, p≈0.5) | Risk score (0–10, proxy) | Liquidity rewards max_spread / min_size |
|---|---:|---:|---:|---:|---|---:|---:|---|
| 2026-03-25 08:00–09:00 | 242,384 | 757.45 | 872.58 | 18 | 0.044–0.083 | 42.08 | 8 | Fetch via rewards API (unknown) |
| 2026-03-24 16:00–17:00 | 181,970 | 568.66 | 655.09 | 18 | 0.044–0.083 | 31.59 | 8 | Fetch via rewards API (unknown) |
| 2026-03-25 09:00–10:00 | 1,926 | 6.02 | 6.93 | 12 | 0.067–0.125 | 0.50 | 2 | Fetch via rewards API (unknown) |
| 2026-03-25 10:00–11:00 | 61 | 0.19 | 0.22 | 7 | 0.114–0.214 | 0.03 | 2 | Fetch via rewards API (unknown) |
| 2026-03-25 11:00–12:00 | 61 | 0.19 | 0.22 | 7 | 0.114–0.214 | 0.03 | 2 | Fetch via rewards API (unknown) |
| 2026-03-25 15:00–16:00 | 45 | 0.14 | 0.16 | 7 | 0.114–0.214 | 0.02 | 2 | Fetch via rewards API (unknown) |

Interpretation:

If you are relying on **maker rebates alone**, reward density is overwhelmingly driven by where taker volume exists (8–9AM and 4–5PM are the only economically meaningful windows in this mini-sample). citeturn21search0turn24view0turn33view0turn32view2turn34view0turn34view1turn34view2turn32view0

If you are relying on **liquidity rewards**, the “dead” windows could become attractive *only if* they carry a meaningful `rate_per_day` and you can be one of few scoring makers; that must be checked in rewards config. citeturn0search8turn10search0turn0search15turn15search18

### Reward density vs competition and risk charts

```mermaid
xychart-beta
    title "Estimated reward density vs competition (proxy) — maker rebates only"
    x-axis "Estimated effective makers (N_eff)" 0 --> 20
    y-axis "Per-maker rebate, USD/hour (p≈0.5 assumption)" 0 --> 45
    series "Windows" [18, 18, 12, 7, 7, 7] [42.08, 31.59, 0.50, 0.03, 0.03, 0.02]
```

```mermaid
xychart-beta
    title "Estimated reward density vs risk proxy (log10(volume+1)) — maker rebates only"
    x-axis "Risk proxy: log10(volume+1)" 1 --> 6
    y-axis "Per-maker rebate, USD/hour (p≈0.5 assumption)" 0 --> 45
    series "Windows" [5.3845, 5.2600, 3.2849, 1.7924, 1.7924, 1.6628] [42.08, 31.59, 0.50, 0.03, 0.03, 0.02]
```

These plots are illustrative: the right way to compute risk is from Binance volatility plus Polymarket last-minute flow (Data API), not from volume alone. citeturn27search0turn28search0turn28search3

## Sensitivity analysis and practical bot recommendations

### Sensitivity to minimum on-book time and heartbeat enforcement

Liquidity rewards (and some scoring mechanisms generally) are sensitive to the minimum “live” duration: if your orders are cancelled too quickly, you may fail to score. Polymarket explicitly offers order scoring verification and references a “required duration” concept. citeturn15search18turn5search18

Separately, the heartbeat mechanism can forcibly cancel all your open orders if you stop heartbeating (10 seconds + buffer), which can wipe scoring time and destroy queue position; therefore, “minimum on-book time” must be considered together with heartbeat cadence and error recovery. citeturn36search0turn36search3

Practical rule:
- Use a heartbeat loop (e.g., every 5 seconds) and treat heartbeat failure as a “global cancel” risk event requiring immediate re-seeding of quotes. citeturn36search0turn36search3
- During weekly restart windows (Mondays 20:00 ET), expect 425 responses; pause order management and retry with exponential backoff. citeturn35search0turn35search1

### Sensitivity to fee regime and probability path

Because effective fee rate depends on \(p(1-p)\) and exponent, the post–Mar 30 crypto regime (exponent 1) makes extreme-probability hours more fee-generative than the current exponent-2 regime, all else equal. This increases maker-rebate pool variance and changes where “reward density” concentrates over time (not only near 50/50). citeturn24view0

If your bot targets the 70th percentile of reward capture, the key is not predicting direction but capturing *a stable share of fee-equivalent fills* while controlling adverse selection. Maker rebates reward liquidity that actually gets taken. citeturn21search0turn24view0

### Sensitivity to competition and maker share

Because rebates are proportional to your share of fee-equivalent within the market, returns scale linearly with your share \(s_i\). citeturn21search0

A quick feasibility bound for maker rebates (crypto, current regime, p≈0.5):
- Maker rebate pool is roughly \(0.2 \times 1.56\% \approx 0.3125\%\) of notional traded. citeturn24view0turn21search0  
- So expected daily rebate is:
  \[
  \text{Rebate} \approx 0.003125 \times V_{\text{day}} \times s
  \]
To generate $1,500/day from rebates alone at \(s=10\%\), you’d need on the order of \(V_{\text{day}}\approx \$4.8\text{M}\) in fee-bearing volume across the markets you participate in—an aggressive target that implies either very large markets or dominant maker share. citeturn21search0turn24view0

### Which windows look best, and why (actionable recommendations)

Given the sample evidence that some hourly windows can be “liquid” while adjacent hours are near-zero volume, the first filter should be:

Target windows where:
1) the market is **fee-enabled** (check `feesEnabled` via market object or query `/fee-rate?token_id=…`), citeturn24view0turn22search8  
2) **volume is consistently high** for that hour-of-day (use Polymarket trades or rolling “Volume” snapshots), citeturn27search0turn33view0turn32view2turn34view0turn34view1turn34view2turn32view0  
3) your expected effective maker count \(N^{eff}\) is not prohibitively high (compute from on-chain OrderFilled maker shares), citeturn26search1turn26search3turn26search0  
4) volatility/toxicity is manageable for your quoting bandwidth (Binance 1h klines + last-5-min imbalance). citeturn28search0turn28search3turn27search0

In the March 24–25 sample, the clear “best” candidates by maker-rebate pool are:
- March 25 8–9AM ET (high volume) citeturn33view0  
- March 24 4–5PM ET (high volume) citeturn32view2  

But: these are also likely to be the most competitive and most toxic near close; use them only if you have tight operational controls.

### Quoting rules to maximize incentives while limiting adverse selection

Maker-leaning execution:
- Use post-only GTC/GTD orders so you never accidentally cross and pay taker fees (post-only rejects crossing orders). citeturn36search0turn36search1
- Maintain strict heartbeat discipline to avoid mass cancellation and lost queue position. citeturn36search0turn36search3
- Respect rate limits; design backoff and batching (CLOB has high limits but you still need safe retries on 429 / 425). citeturn27search7turn35search0turn35search1

Liquidity rewards compliance posture:
- If (and only if) a market is in the rewards program, quote within `rewards_max_spread` and at/above `rewards_min_size`, and periodically verify scoring status. citeturn10search0turn15search18turn5search18

Adverse selection mitigation (hourly BTC-specific):
- Stagger quote tightening: widen early in the hour, tighten mid-hour when volatility is lower, widen again in the last few minutes, because last-minute flow is most likely to be informed (this needs to be statistically verified with trade-tape imbalance and Binance volatility). citeturn27search0turn28search0turn28search3
- Cancel/replace cadence should be bounded by rate limits and by the risk of losing time priority; frequent cancels also make liquidity-reward scoring harder in regimes with minimum on-book time. citeturn10search0turn27search7turn15search18

## Limitations, assumptions, and compliance notes

Data availability and representativeness:
- The “top windows” table is based on a small sample of market pages (March 24–25) and uses an explicit p≈0.5 effective-fee assumption; it should be treated as an illustrative example of the methodology, not a definitive population-level ranking. citeturn33view0turn34view0turn34view1turn34view2turn32view0turn32view2turn24view0
- True competition and concentration must be measured from on-chain OrderFilled maker shares on the CTF Exchange (maker/taker/fee fields). citeturn26search1turn26search3turn26search0
- Liquidity rewards parameters (pool sizes, constraints) are market-specific and must be fetched; if a market is not in the rewards list, its liquidity reward pool is effectively zero. citeturn10search0turn0search15

Operational risks:
- Matching engine restarts (weekly Monday 20:00 ET) create temporary downtime and HTTP 425 errors; bots must implement retry/backoff or risk cascaded failures. citeturn35search0turn35search1
- Heartbeat failures can trigger forced cancellation of all open orders, which is catastrophic for both fill share and any on-book-time-based scoring. citeturn36search0turn36search3
- Abuse prevention: orders are monitored for validity (balances, allowances, cancellations), and the docs warn that abusive behavior can lead to blacklisting; treat incentive-farming strategies as compliance-sensitive engineering. citeturn36search0turn26search1

Regulatory/compliance:
- This analysis is technical and does not constitute financial advice.
- Ensure your bot complies with Polymarket terms, API rules, and any jurisdictional restrictions applicable to you.
- On-chain monitoring uses published contract addresses on entity["organization","Polygon","blockchain network"] (Chain ID 137) and publicly emitted `OrderFilled` events; avoid any behavior that could be interpreted as manipulation or wash trading. citeturn26search0turn26search1