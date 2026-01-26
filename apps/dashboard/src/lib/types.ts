// API Types based on docs/api-contracts.md

export interface MetricsSummary {
  total_pnl: string;
  total_pnl_percent: string;
  sharpe_ratio: string;
  max_drawdown: string;
  win_rate: string;
  total_trades: number;
  active_positions: number;
  capital_deployed: string;
  available_capital: string;
  equity_curve: EquityPoint[];
}

export interface EquityPoint {
  date: string;
  value: string;
}

export interface Strategy {
  strategy_id: string;
  name: string;
  description: string;
  status: "active" | "inactive";
  mode: "BACKTEST" | "PAPER" | "LIVE";
  universe_size: number;
  max_positions: number;
  risk_per_trade_pct: string;
  created_at: string;
  updated_at: string;
  config?: StrategyConfig;
  performance?: StrategyPerformance;
}

export interface StrategyConfig {
  model_type?: string;
  features?: string[];
  signal_threshold?: number;
  stop_loss_pct?: string;
  take_profit_pct?: string;
}

export interface StrategyPerformance {
  total_pnl: string;
  sharpe_ratio: string;
  max_drawdown: string;
  win_rate: string;
}

export interface Position {
  position_id: string;
  strategy_id: string;
  symbol: string;
  contract_type: "STOCK" | "OPTION";
  quantity: string;
  average_entry_price: string;
  current_price: string;
  unrealized_pnl: string;
  unrealized_pnl_pct: string;
  market_value: string;
  opened_at: string;
  days_held: number;
}

export interface Run {
  run_id: string;
  strategy_id: string;
  run_type: "BACKTEST" | "PAPER" | "LIVE";
  start_date: string;
  end_date: string;
  total_return: string;
  sharpe_ratio: string;
  max_drawdown: string;
  total_trades: number;
  status: "RUNNING" | "COMPLETED" | "FAILED";
  report_url?: string;
  created_at: string;
  completed_at?: string;
}

export interface RunDetail extends Run {
  metrics: RunMetrics;
  equity_curve: EquityPoint[];
  trades: Trade[];
}

export interface RunMetrics {
  total_return: string;
  cagr: string;
  sharpe_ratio: string;
  sortino_ratio: string;
  max_drawdown: string;
  win_rate: string;
  profit_factor: string;
  total_trades: number;
  avg_trade_duration_hours: string;
}

export interface Trade {
  trade_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: string;
  entry_price: string;
  exit_price: string;
  pnl: string;
  pnl_pct: string;
  entry_time: string;
  exit_time: string;
}

export interface Alert {
  alert_id: string;
  severity: "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  message: string;
  context?: Record<string, unknown>;
  acknowledged: boolean;
  created_at: string;
}

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  services: Record<string, ServiceHealth>;
  timestamp: string;
}

export interface ServiceHealth {
  status: "healthy" | "degraded" | "unhealthy";
  latency_ms?: number;
  last_update?: string;
  staleness_seconds?: number;
  broker?: string;
  mode?: string;
}

// API Response wrappers
export interface ApiResponse<T> {
  data: T;
  meta?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total_count: number;
    page: number;
    per_page: number;
  };
}
