# Deep Research: Polymarket BTC “Up/Down” Trading Bots in Hour-Long Windows

## Why this idea is getting buzz right now

A big part of the recent “Polymarket bot” chatter is structural: the platform increasingly resembles an algorithm-friendly exchange (central limit order book + real-time feeds + official SDKs), and it has rolled out multiple explicit incentives and market formats that tend to attract automated traders.

Since early January 2026, several platform changes likely increased bot interest:

Polymarket’s own changelog shows a rapid sequence of updates that are directly relevant to systematic crypto trading and market making: taker fees and maker rebates were enabled on 15‑minute crypto markets (Jan 5, 2026), the platform added new API features including a HeartBeats endpoint and post‑only order behavior (Jan 6, 2026), it launched 5‑minute crypto markets with fees (Feb 12, 2026), and it expanded taker fees + maker rebates to all crypto markets including 1H products starting March 6, 2026. citeturn13view0 These are exactly the kinds of changes that push traders toward stable automation (to react quickly, quote continuously, and manage cancellations safely).

The fee picture is also changing again soon. The current fee schedule states that “new fee parameters will take effect on March 30, 2026,” and that the fee model will expand beyond crypto + sports to additional categories (finance, politics, weather, etc.) with updated parameters. citeturn35view0 Even if your strategy focuses on BTC hourlies, fee regime changes matter because they alter (a) whether you want to be maker vs taker, and (b) the expected “tax” on high-frequency style strategies. citeturn35view0

Finally, there has been notable mainstream and regulatory scrutiny around prediction markets in March 2026, which also contributes to “buzz” (both as hype and as risk). For example, entity["organization","Major League Baseball","us pro baseball league"] announced a partnership with Polymarket and a memorandum of understanding with the entity["organization","Commodity Futures Trading Commission","us derivatives regulator"] focused on integrity monitoring. citeturn8news34 Meanwhile, news coverage has highlighted policy debates and proposed legislation aimed at restricting certain prediction-market products (especially sports-style contracts) on federally regulated venues. citeturn8news32turn8news35 Even if you’re trading BTC direction markets, the broader environment can affect listings, enforcement, and platform rules. citeturn8news35

## How Polymarket’s short-horizon crypto markets work

### The “Up/Down” contract is a binary payout claim

On Polymarket, each market is fundamentally a **binary Yes/No claim** with outcome tokens (one for each side). A market has identifiers like a condition ID and token IDs (ERC‑1155 tokens) for trading on the order book. citeturn32view0 Prices represent **implied probabilities** (e.g., 0.20 vs 0.80) and the outcomes map 1:1 to those prices. citeturn37view1 When the market resolves, shares of the correct outcome are redeemable for **$1 per share**, and incorrect outcomes go to $0—this payoff mechanic is explicitly described on the BTC “Up/Down” market pages. citeturn31view0turn7view0

### Hourly BTC “Up/Down” markets are anchored to Binance 1‑hour candles

For the hourly BTC product your friend described (trading a single 1-hour window each day), Polymarket’s own rule text on the hourly contract pages is unambiguous: the market resolves “Up” if the **closing price is greater than or equal to the opening price** for the BTC/USDT 1‑hour candle beginning at the specified time, and “Down” otherwise, with the resolution source explicitly being entity["company","Binance","crypto exchange"] (BTC/USDT). citeturn6view2turn31view0

Two practical implications for bot builders:

These hourly markets can open **days before the hour they reference**, so a bot can pre-discover the next day’s 9–10AM ET contract (or whatever time window you care about) rather than scrambling at the last second. For example, the “Bitcoin Up or Down – March 24, 9–10AM ET” page shows “Market Opened: Mar 22, 2026, 9:00 AM ET.” citeturn31view0

Liquidity can be meaningful even in a single hourly window. That same March 24, 9–10AM ET market shows $139,900 in trading volume. citeturn31view0 This helps frame whether a “one-market-per-day” approach has enough flow to support market making or repeated entries/exits.

### 15‑minute and 5‑minute BTC “Up/Down” markets use Chainlink data streams

Shorter BTC “Up/Down” markets (e.g., 5-minute, 15-minute) have similar “end price ≥ start price” criteria—but the data source differs. The 5‑minute BTC window market resolves based on the entity["company","Chainlink","oracle network"] BTC/USD data stream (and explicitly warns that it is about that stream, not other spot sources). citeturn7view0 A 15‑minute BTC window page similarly states the resolution source is Chainlink’s BTC/USD data stream. citeturn0view2turn5search8

This matters because a “smart algorithm” that feeds on Binance prices may track the hourly product well, but it can be miscalibrated for the 5m/15m products if Chainlink stream dynamics differ from Binance spot/perp prices (lag, aggregation, or microstructure differences). citeturn7view0turn0view2

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["Polymarket BTC up or down hourly market order book","Polymarket BTC up or down 5 minute market rules Chainlink screenshot","Polymarket rewards page limit order liquidity rewards screenshot","Polymarket clob api websocket market channel documentation screenshot"],"num_per_query":1}

## What a “one-market, one-hour-per-day bot” actually does

Even when people say “prediction bot,” most real systems fall into one (or a hybrid) of the following trade styles.

### Model-driven directional trading

This bot tries to estimate the true probability of “Up” for that specific hour and trades when the market price deviates.

A core mechanical point: the “Up” event (close ≥ open) becomes progressively more “knowable” as the hour evolves because you observe the live BTC/USDT price versus the hour’s open. The market’s implied probability *should* move as that happens (and Polymarket’s own pages describe odds updating as traders react to the evolving live price action). citeturn28view0turn31view0 A bot’s potential edge is essentially: “my probability update is faster/better calibrated than the crowd’s.”

The challenge has become larger since January 2026 because taker fees introduce a meaningful hurdle for high-frequency directional entry/exit when you cross the spread. Polymarket’s fee documentation shows that under the currently live structure, crypto trades peak at an effective taker fee rate of about **1.56% at 50% probability** (for a 100-share example), and the fee curve is symmetric (lower at extremes, highest around 0.50). citeturn35view0 After March 30, 2026, the updated crypto fee parameterization implies a peak effective fee rate of **1.80%** at 50%. citeturn35view0

So if the bot is “taking” liquidity (marketable orders), its forecast edge must clear: spread + slippage + taker fee + adverse selection (in fast markets). citeturn35view0turn42view0

### Spread capture and incentives via market making

A second class of systems doesn’t need a strong directional forecast; it profits (when it does) from (a) capturing spread as a maker and (b) earning incentive payouts for providing liquidity.

Polymarket explicitly defines market makers as traders who continuously post bid/ask orders and earn spread as compensation for risk. citeturn14view3 And it explicitly runs a Liquidity Rewards program: by posting resting limit orders, liquidity providers are “automatically eligible,” and rewards are distributed daily (midnight UTC) to maker addresses. citeturn14view0turn14view1 The methodology emphasizes tight, balanced quoting near the midpoint and is inspired by entity["organization","dYdX Foundation","dex ecosystem org"] style LP rewards. citeturn14view0

Separate from Liquidity Rewards, Polymarket also funds a Maker Rebates program using taker fees: rebates are paid daily in USDC, performance-based, and proportional to the share of maker liquidity that actually gets taken (and therefore “generates” fee-equivalent value). citeturn41view0turn35view0 Critically, maker rebates are calculated per market (“you only compete with other makers in the same market”). citeturn41view0

For an “8–9AM every day” schedule, a pure market maker can still make sense if (1) the targeted hour’s market consistently has volume and (2) the reward pool for that market is significant compared to competition. The platform even provides a dedicated “Daily Rewards” page where you can see per-market reward budgets and eligibility parameters (max spread, min shares). citeturn17view0turn14view1

### A realistic hybrid for hourly BTC markets

Many serious systems blend the two:

Quote both sides (post-only) around a model “fair value” probability, earn maker-style benefits, but also **skew inventory** if the model suggests a directional drift or if the current BTC price is far above/below the hour’s open. citeturn34view0turn31view0

Use “post-only” behavior so accidental marketable orders get rejected (guaranteeing you’re a maker rather than taker on that order). citeturn34view0

Keep a fast “kill switch” so you can cancel all orders on errors or state divergence. Polymarket has an explicit cancel-all endpoint. citeturn34view3

This hybrid approach is broadly consistent with where platform incentives point: tighten spreads, add depth, and quote consistently, while still managing directional risk. citeturn14view0turn41view0

## Unit economics and realism check on “$1,500/day”

“$1,500/day average” from trading one hourly BTC market each day is not *impossible*, but it is the kind of number that typically requires at least one of (a) substantial capital, (b) consistently strong edge, (c) significant reward pool capture, or (d) a short-lived market inefficiency.

### What volume looks like in a single one-hour BTC “Up/Down” market

A concrete data point: one hourly BTC “Up/Down” contract (March 24, 9–10AM ET) shows **$139.9K** volume. citeturn31view0 Another adjacent hour (March 24, 8–9AM ET) shows **$110.4K** volume. citeturn30view0

At that scale, the *total available “pie”* for a market maker is limited by (a) how much of that flow hits your resting orders, and (b) how much spread you can capture without getting adversely selected. The maker rebate pool is a percentage of taker fees collected, and for crypto the maker rebate percentage is listed as 20% in the maker rebates documentation. citeturn41view0turn35view0

A rough implication: even if an hourly market had ~$140K of trade value, total taker fees would be on the order of (average effective fee rate) × $140K. Since the crypto fee curve peaks around ~1.56% near 0.50 (current) and is lower far from 0/1, the *average* fee rate could easily be well below the maximum; regardless, a 20% maker rebate share means the maker rebate pool is only a fraction of already modest fee totals. citeturn35view0turn41view0 That makes it difficult for maker rebates alone to explain $1,500/day from one hour unless the market is much larger than these examples or you capture an unusually dominant share of the market’s maker score. citeturn41view0turn31view0

### Fees are a major headwind for “taker-style” intraday trading

For crypto, Polymarket’s published fee tables show a 100-share trade at 0.50 has a $0.78 fee on $50 trade value (1.56% effective). citeturn35view0 In a strategy that repeatedly buys and sells within the hour using marketable orders, these fees can dominate expected value unless your model edge is large and stable or you trade mostly at extreme probabilities (where fees are lower). citeturn35view0turn42view0

The upcoming March 30, 2026 structure implies an even higher peak effective fee rate for crypto (1.80% at 50%). citeturn35view0 This will further raise the bar for “in-and-out” taking strategies in mid-probability regimes.

### The broader distribution of outcomes suggests consistent profits are hard

Independent reporting suggests a large fraction of participants lose money in aggregate, with profit concentration among a small tail of accounts. For example, an analysis described by Finance Magnates (based on “defioasis.eth” on-chain data) reports roughly **70% of Polymarket trading addresses recorded realized losses**, and that a very small fraction captured a very large share of realized profits. citeturn27view0 The Defiant similarly reports that researchers analyzing a very large trade dataset found only around 30% of accounts ended with net gains. citeturn27view2

You don’t need to accept these values as perfect truth to take the key lesson: a persistent profitable edge tends to be concentrated among systematic, well-capitalized, or infrastructure-advantaged participants—exactly the group you’re trying to join. citeturn27view0turn27view2

## What counts as credible success stories in the “bot” context

Because “tech Twitter” success stories are often unverifiable or selectively shared, the most credible signals for bot profitability are the ones that (a) you can cross-check and (b) imply scale without relying on screenshots.

### Platform-level evidence that highly profitable traders exist

Polymarket’s own leaderboard shows very large profits at the top end for different time windows and categories. For example, the overall weekly leaderboard lists multi-million dollar profit/loss figures among top accounts. citeturn19view0 The crypto monthly leaderboard shows top accounts with hundreds of thousands in profit with very high volume (tens of millions). citeturn19view1

This is not proof those accounts are bots—but the combination of high volume and consistent leaderboard presence is the kind of footprint that is often associated with automation or at least highly systematic execution. citeturn19view1turn21view0 (The API even exposes leaderboard data programmatically, including `pnl` and `vol` fields.) citeturn21view0

### Platform-level evidence that incentives are designed for continuous quoting

Two direct “bot magnets” are formalized:

Liquidity Rewards: rewards paid daily (midnight UTC) and designed to motivate tight, balanced quoting near midpoints. citeturn14view0turn14view1 The March 17, 2026 changelog entry (focused on March Madness markets) even highlights constraints like a minimum order-on-book time (3.5 seconds) for eligibility, which is the kind of rule that naturally pushes toward automated quote maintenance. citeturn13view0

Maker Rebates: paid daily in USDC, funded by taker fees, and computed based on executed maker liquidity (fee-equivalent weighting). citeturn41view0turn35view0

These programs are credible on their face because they are documented by the platform and can be cross-checked via activity types in the public Data API (e.g., `REWARD` and `MAKER_REBATE` show up as activity types). citeturn21view1

### Credible “bot builder” artifacts and how to interpret them

Open-source bots and reference implementations are credible evidence that a bot *can be built*, but not that it will be profitable now.

For example, a GitHub project (“Poly‑Maker”) explicitly describes itself as a market making bot (WebSocket order book monitoring, risk controls, etc.)—but also explicitly warns that “in today’s market, this bot is not profitable and will lose money,” citing increased competition. citeturn12view0 That warning is itself a valuable, credibility-boosting signal: it aligns with the “arms race” narrative and suggests naïve liquidity farming is not a free lunch. citeturn12view0turn27view2

## Building toward a bot that can plausibly reach the “70th percentile”

Below is a research-to-build blueprint that focuses on the mechanics *most likely* to separate a “toy bot” from a robust system—while staying realistic about competition.

### Get the mechanics right first

Polymarket is designed as a CLOB with off-chain matching and on-chain settlement. Orders are EIP‑712 signed, and matched trades settle atomically; the docs emphasize non-custodial trading and that the operator cannot execute unauthorized trades. citeturn4view0turn34view0

From a bot perspective, there are three foundational APIs (Gamma for discovery, Data for positions/trades/activity/leaderboards, and CLOB for orderbook + execution) plus a Bridge API for deposits/withdrawals. citeturn37view0 The market data endpoints are public (no auth), while trading endpoints require authentication. citeturn37view0turn4view2

### Use real-time data feeds, not polling

The docs recommend using WebSocket market channels for real-time order book and market events rather than polling. citeturn9view2turn4view3 This matters for hourly BTC markets because “fair value” can move quickly as BTC moves relative to the hour’s open (especially near the end of the hour), and stale quotes are a fast way to get picked off. citeturn31view0turn42view0

### Engineer safety rails that prevent catastrophic failure modes

Polymarket provides built-in patterns that should be treated as mandatory for serious automation:

Heartbeats: the “heartbeat endpoint maintains session liveness,” and if a valid heartbeat isn’t received within ~10 seconds (plus buffer), open orders are canceled. citeturn34view2turn34view4 This is explicitly described as useful for automated trading systems to ensure orders are canceled if the system becomes unresponsive. citeturn34view4

Cancel-all: explicit API support exists to cancel all open orders for the authenticated user. citeturn34view3

Post-only logic: “post-only orders” are rejected if they would match immediately, guaranteeing you are always maker, never taker for that order. citeturn34view0 In fee-heavy environments, being able to enforce maker behavior is crucial. citeturn35view0turn34view0

Planned downtime handling: the matching engine restarts weekly on Tuesdays at 7:00 AM ET, typically ~90 seconds, and returns HTTP 425 on order-related endpoints. The docs provide a recommended retry strategy. citeturn34view1 A bot that trades “8–9AM daily” is close enough to this window that you should explicitly test restart handling (especially on Tuesdays). citeturn34view1

Rate limits and throttling: Polymarket enforces rate limits via entity["company","Cloudflare","web infrastructure company"] throttling; exceeding limits can queue and delay requests rather than cleanly failing. citeturn4view1 This can create hidden latency spikes that break strategies that assume consistent response times.

### Backtest the *right* thing: fee-aware, latency-aware edge

To get to “~70th percentile,” you don’t necessarily need a genius predictor—but you do need to avoid the common traps:

Use orderbook-derived prices. Polymarket explains that displayed prices are midpoints of bid/ask (unless the spread is >$0.10, then last trade is used), so your bot should not assume the UI probability equals executable price. citeturn42view0turn37view1

Model fees explicitly. The fee curve is non-linear and peaks near 0.50; it is also changing March 30, 2026. citeturn35view0 If your bot’s expected edge per trade is not comfortably larger than fee + spread in the targeted regime, the strategy is structurally negative EV.

Prefer maker execution where feasible. Maker rebates and liquidity rewards are designed to reward “competitive quoting” and “orders that add liquidity to the book and get filled.” citeturn41view0turn14view0

### Compliance and availability matter if you’re in the U.S.

Polymarket’s site footer indicates it operates globally through separate legal entities; entity["company","QCX LLC","dba polymarket us"] d/b/a entity["organization","Polymarket US","cftc dcm qcx llc"] is described as a CFTC-regulated designated contract market, while the international platform is not regulated by the CFTC and operates independently. citeturn7view0turn16search7 The CFTC’s own industry filings list QCX LLC d/b/a Polymarket US as a designated contract market (status “Designated,” date 2025‑07‑09). citeturn40view0turn40view1

In practical terms: make sure your engineering plan assumes you’ll stay within the rules and product availability of the venue you can legally access (especially if you are physically in the U.S.). citeturn40view0turn40view2

## Three deep research prompts to go beyond baseline

### Market microstructure research for hourly BTC “Up/Down” contracts

**Prompt:** “Build a fee-curve-aware microstructure model of hourly BTC ‘Up/Down’ markets and identify the dominant sources of PnL for a maker-leaning strategy.”

Minimum deliverables should include: (1) a decomposition of realized PnL into spread capture vs inventory drift vs incentive payouts (liquidity rewards + maker rebates), (2) sensitivity to quote distance from midpoint and minimum on-book time constraints, and (3) a robust simulation of ‘toxic flow’ near the hour close where price moves quickly and the probability races toward 0/1. Anchor the study on the published taker fee curve and the documented maker rebate mechanism. citeturn35view0turn41view0turn14view0

### Probability-of-close modeling using Binance-aligned signals

**Prompt:** “Estimate the true probability that the BTC/USDT 1-hour candle closes up, conditional on intra-hour price path, and test whether Polymarket probabilities lag that estimate.”

Because hourly markets explicitly settle on Binance candle open/close, design a modeling pipeline that uses Binance-aligned features (distance-to-open, realized volatility, orderbook imbalance, perp funding, and event-time-of-day effects). Then backtest whether mispricings (model probability minus implied probability) persist long enough to overcome fees and spreads, with special attention to the post-March-6 fee/rebate expansion across hourly crypto markets and the upcoming March-30 fee changes. citeturn31view0turn13view0turn35view0

### Competition mapping and “reward pool selection” to avoid the red ocean

**Prompt:** “Treat rewards and rebates as a competitive game: identify which markets and time windows offer the best ‘reward density’ per unit of competition and risk.”

Use the platform’s Daily Rewards UI and documented reward logic to build a ranking of markets by: reward size, max spread, minimum size, and observed competitor concentration. citeturn17view0turn14view1turn14view0 Combine this with a hypothesis about why some markets show >$100K hourly volume while others are thin, and how that affects the feasibility of earning both rebates and spread without getting adverse-selected. citeturn31view0turn41view0

If your goal is “~70th percentile,” the strategic implication of these three prompts is: you don’t have to beat the best bots; you have to (1) avoid structural negative-EV regimes (fees + spread), (2) avoid the most toxic flow periods unless you have latency and modeling to survive them, and (3) pick reward/flow niches where competition is not yet saturated. citeturn35view0turn12view0turn27view2