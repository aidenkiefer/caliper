/**
 * Type definitions for Model Observatory Dashboard (Sprint 9)
 */

export type ModelType = 'logistic' | 'tree' | 'ensemble';
export type ModelStatus = 'active' | 'paused' | 'retired' | 'candidate';

export interface Model {
  id: string;
  name: string;
  type: ModelType;
  status: ModelStatus;
  trainedDate: string;
  healthScore: number;  // 0-100
  allocationWeight: number;  // 0-1
  accuracy: number | null;
  abstentionRate: number;
  metadata: {
    features: number;
    samples: number;
    trainingPeriod: [string, string];
    modelType: string;
  };
}

export interface PerformanceMetrics {
  model_id: string;
  window_days: number;
  total_predictions: number;
  completed_predictions: number;
  abstained_predictions: number;
  abstention_rate: number;
  accuracy: number | null;
  avg_confidence: number | null;
  correct_avg_confidence: number | null;
  incorrect_avg_confidence: number | null;
  timestamp: string;
}

export interface DriftMetrics {
  model_id: string;
  feature_metrics: Array<{
    feature: string;
    psi: number;
    kl_divergence: number;
    mean_shift: number;
  }>;
  confidence_metric: {
    psi: number;
    kl_divergence: number;
  } | null;
  timestamp: string;
}

export interface HealthScore {
  model_id: string;
  health_score: number;
  components: {
    feature_drift: number;
    confidence_drift: number;
    error_drift: number;
    staleness: number;
  };
  alerts: string[];
  timestamp: string;
}

export interface BaselineComparison {
  strategy_id: string;
  strategy_return: number;
  baseline_returns: Record<string, number>;
  regret_metrics: Record<string, number>;
  outperforms: Record<string, boolean>;
}

export interface Recommendation {
  recommendation_id: string;
  strategy_id: string;
  signal: 'BUY' | 'SELL' | 'ABSTAIN';
  symbol: string;
  confidence: number;
  uncertainty: number;
  timestamp: string;
  explanation_id: string | null;
}

export interface ModelConfig {
  abstain_threshold: number;
  low_confidence_threshold: number;
  high_confidence_threshold: number;
  position_size_pct: number;
}

export type RankedMarketSide = "YES" | "NO";
export type FleetRegime = "R1" | "R2" | "R3" | "R4" | "R5";
export type FleetMode = "paper" | "live";
export type FleetSignalDirection = "long" | "short" | "none" | "abstain";
export type FleetSignalAction = "executed" | "rejected" | "abstained" | "cancelled";
export type FleetStrategyStatus = "active" | "paused" | "cooldown" | "abstain";
export type PaperTradeStatus = "filled" | "simulated" | "cancelled";

export interface RankedMarket {
  market_id: string;
  market_name: string;
  condition_id: string;
  side: RankedMarketSide;
  score: number;
  ev_adj: number;
  feasibility: number;
  confidence: number;
  spread_pct: number;
  volume_24h_usd: number;
  time_to_close_seconds: number;
  selected: boolean;
  cooldown_protected: boolean;
}

export interface RankedUniverse {
  ranked_at: string;
  total_candidates: number;
  selected_markets: RankedMarket[];
  excluded_markets: string[];
  ranking_method: string;
  cooldown_protected: string[];
  candidate_markets: RankedMarket[];
}

export interface FleetStrategyCard {
  strategy_id: string;
  name: string;
  status: FleetStrategyStatus;
  mode: FleetMode;
  current_regime: FleetRegime;
  pnl_24h_usd: number;
  sharpe_7d: number;
  fill_rate: number;
  allocation_weight: number;
  regime_alignment: number;
  signal_count_24h: number;
}

export interface RegimeTimelinePoint {
  timestamp: string;
  regime: FleetRegime;
  allocation_weights: Record<string, number>;
}

export interface StrategyComparisonRow {
  strategy_id: string;
  baseline: string;
  sharpe_7d: number;
  sortino_7d: number;
  win_rate: number;
  max_drawdown: number;
  profit_factor: number;
}

export interface FleetStatus {
  generated_at: string;
  current_regime: FleetRegime;
  current_mode: FleetMode;
  strategies: FleetStrategyCard[];
  regime_timeline: RegimeTimelinePoint[];
  comparison: StrategyComparisonRow[];
}

export interface FleetSignal {
  signal_id: string;
  timestamp: string;
  strategy_id: string;
  market_id: string;
  signal_type: string;
  direction: FleetSignalDirection;
  confidence: number;
  action_taken: FleetSignalAction;
  fill_price?: number | null;
  regime: FleetRegime;
}

export interface PaperTrade {
  trade_id: string;
  timestamp: string;
  strategy_id: string;
  market_id: string;
  side: "BUY" | "SELL";
  price: number;
  size: number;
  pnl_usd: number;
  status: PaperTradeStatus;
}
