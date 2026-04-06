/**
 * Centralized help strings for HelpHint (tooltip + mobile sheet).
 * Keys are stable IDs for future glossary sync.
 */
export const HELP_COPY: Record<
  string,
  { title: string; body: string; readMoreHref?: string }
> = {
  "overview-kpis": {
    title: "Portfolio KPIs",
    body: "These cards summarize paper or simulated equity performance from the dashboard API: profit/loss, risk-adjusted return (Sharpe), worst peak-to-trough loss (drawdown), and how much capital is in use. They are not Polymarket bot metrics unless wired together later.",
    readMoreHref: "/help",
  },
  "overview-equity-chart": {
    title: "Equity curve",
    body: "A time series of account value. Use it to see smooth growth vs choppy periods. Compare with baselines below to see if the strategy beat simple alternatives.",
  },
  "overview-alerts": {
    title: "Alerts",
    body: "System and strategy notices (risk, data delays, model health). Acknowledge items you have reviewed so your queue stays actionable.",
  },
  "sprint16-fleet": {
    title: "Sprint 16 fleet & ranker",
    body: "Cross-sectional market ranking and a multi-strategy paper fleet. Today the REST endpoints for ranking and fleet are contract-complete but return mock JSON until wired to the live ranker and paper-trade store. Regime/allocation APIs read real database rows when DB_URL is set on the server.",
    readMoreHref: "/platform",
  },
  "model-observatory": {
    title: "Model Observatory",
    body: "Lifecycle UI for ML models: registry, performance, drift, explanations, and human-in-the-loop review. Connects to the ML safety APIs when backend data is real.",
    readMoreHref: "/models",
  },
  "baseline-comparison": {
    title: "Baseline comparison",
    body: "Compares your strategy return to simple benchmarks: hold cash, buy-and-hold, and a random policy. Regret metrics show how much you gained or lost versus each baseline.",
  },
  "start-page": {
    title: "Getting started",
    body: "Work through these steps once. Use Done when finished, Skip if you will do it later, or N/A if the step does not apply (e.g. you are not using Polymarket). Progress is saved only in this browser.",
  },
  "platform-hub": {
    title: "Platform map",
    body: "Every major capability in one place. Status badges tell you whether data is live from the API, mocked for UI preview, stubbed, CLI-only, or documented in-repo only.",
    readMoreHref: "/help",
  },
  "platform-features": {
    title: "Feature snapshots",
    body: "Sprint 12 unified features for Polymarket markets: four families (market state, microstructure, BTC-linked probability inputs, regime labels). Data is read from pm.features when the API has DB_URL. Enter a market_id (token or condition id as used by your pipeline).",
    readMoreHref: "/platform",
  },
  "features-market-state": {
    title: "Market state family",
    body: "Prices, spread, book depth, and timing relative to the trading window. Describes how the market looks right now.",
  },
  "features-microstructure": {
    title: "Microstructure family",
    body: "Order flow, imbalance, toxicity proxies, fees, and reward eligibility. Useful for market-making and execution quality.",
  },
  "features-probabilistic": {
    title: "Probabilistic (BTC) family",
    body: "Derived from Binance / reference BTC data: realized vol, momentum, funding, basis. Feeds regime detection and probability models.",
  },
  "features-regime": {
    title: "Regime family",
    body: "Discrete labels (vol, trend, time bucket, toxicity, spread quality) and scores. Used by Sprint 15 allocation and Sprint 16 strategies.",
  },
  "features-advanced-json": {
    title: "Raw JSON",
    body: "Full API payload for debugging or copying into notebooks. Can be large; keep collapsed unless you need it.",
  },
  "explorer-polymarket": {
    title: "Polymarket sessions",
    body: "Lists market-making sessions from pm.* via GET /v1/polymarket/sessions. The API may return mock or empty data until the database pool is wired in services/api. Open a row to see orders and fills for that session.",
    readMoreHref: "/help",
  },
  "explorer-polymarket-session": {
    title: "Session detail",
    body: "Per-session orders, fills, and summary fields. Detail GET may 404 until real DB queries land; list view still documents the contract.",
  },
  "explorer-regime-allocation": {
    title: "Regime & allocation",
    body: "Sprint 15: global and per-market regime states, allocation decisions, and the rolling performance matrix. Requires DB_URL on the API. History endpoints need ISO start/end times.",
    readMoreHref: "/platform",
  },
  "explorer-probability": {
    title: "BTC probability model",
    body: "Sprint 14: calibration reports, lag tests, and per-market predictions. Several routes return stub/mock payloads until wired to pm.probability_predictions; still useful for learning the contract.",
    readMoreHref: "/platform",
  },
  "explorer-simulation": {
    title: "Simulation & evaluation",
    body: "Sprint 13: queue a CLOB replay run, poll SimResult, and fetch evaluation reports. Handlers are stub/in-memory today—responses show shape and zeros until wired to SimulationRunner and pm.simulation_runs.",
    readMoreHref: "/platform",
  },
  "explorer-ranking-fleet": {
    title: "Ranking & fleet",
    body: "Sprint 16: RankedUniverse plus fleet status, signals, and paper trades. Ranking and fleet GETs require DB_URL but return fixed mock JSON until handlers call MarketRanker and PaperTradeStore.",
    readMoreHref: "/platform",
  },
  "explorer-equities": {
    title: "Equities hub",
    body: "Entry points for Alpaca-oriented flows: strategies, runs, and portfolio metrics on Overview. Execution and risk are server-side; this page only links to dashboard areas.",
    readMoreHref: "/start",
  },
};
