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
