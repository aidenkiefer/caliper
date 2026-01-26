export interface GlossaryTerm {
  term: string;
  definition: string;
  category: 'performance' | 'risk' | 'position' | 'strategy';
  example?: string;
}

export const glossaryTerms: GlossaryTerm[] = [
  {
    term: "P&L",
    definition: "Profit and Loss - the money made or lost on trades",
    category: "performance",
    example: "+$450 means you made $450"
  },
  {
    term: "Sharpe Ratio",
    definition: "Risk-adjusted return metric. Higher = better risk-adjusted performance. >1 is good, >2 is excellent",
    category: "performance"
  },
  {
    term: "Max Drawdown",
    definition: "Largest peak-to-trough decline in portfolio value. Measures worst-case loss",
    category: "risk",
    example: "-15% means at worst you were down 15% from peak"
  },
  {
    term: "Win Rate",
    definition: "Percentage of trades that were profitable",
    category: "performance"
  },
  {
    term: "Profit Factor",
    definition: "Gross profit / gross loss. >1 means profitable overall",
    category: "performance"
  },
  {
    term: "Drawdown",
    definition: "Current decline from the portfolio's peak value",
    category: "risk"
  },
  {
    term: "Long",
    definition: "Buying an asset expecting price to rise",
    category: "position"
  },
  {
    term: "Short",
    definition: "Selling borrowed asset expecting price to fall",
    category: "position"
  },
  {
    term: "Entry Price",
    definition: "The price at which a position was opened",
    category: "position"
  },
  {
    term: "Mark Price",
    definition: "Current market price of the asset",
    category: "position"
  },
  {
    term: "Unrealized P&L",
    definition: "Profit or loss on open positions that haven't been closed yet",
    category: "position"
  },
  {
    term: "Stop Loss",
    definition: "A price level that triggers automatic sell to limit losses",
    category: "risk"
  },
  {
    term: "Take Profit",
    definition: "A price level that triggers automatic sell to lock in gains",
    category: "risk"
  },
  {
    term: "Backtest",
    definition: "Testing a trading strategy on historical data to see how it would have performed",
    category: "strategy"
  },
  {
    term: "Paper Trading",
    definition: "Simulated trading with fake money to test strategies without risk",
    category: "strategy"
  },
  {
    term: "Live Trading",
    definition: "Trading with real money in live markets",
    category: "strategy"
  },
  {
    term: "Signal",
    definition: "A recommendation from the model to BUY, SELL, or HOLD",
    category: "strategy"
  },
  {
    term: "ABSTAIN",
    definition: "When the model chooses not to trade due to low confidence",
    category: "strategy"
  },
  {
    term: "Confidence",
    definition: "How certain the model is about its prediction (0-100%)",
    category: "strategy"
  },
  {
    term: "Model Drift",
    definition: "When a model's performance degrades because market conditions have changed",
    category: "strategy"
  },
  {
    term: "SHAP",
    definition: "A method to explain which features most influenced a model's prediction",
    category: "strategy"
  }
];

export function getTermsByCategory(category: string): GlossaryTerm[] {
  return glossaryTerms.filter(t => t.category === category);
}

export function searchTerms(query: string): GlossaryTerm[] {
  const lower = query.toLowerCase();
  return glossaryTerms.filter(t => 
    t.term.toLowerCase().includes(lower) ||
    t.definition.toLowerCase().includes(lower)
  );
}
