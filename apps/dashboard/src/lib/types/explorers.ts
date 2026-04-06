/** Polymarket session analytics (API JSON). */
export interface PolymarketSessionRow {
  session_id: string;
  market_condition_id: string;
  token_id_yes: string;
  window_start: string;
  window_end: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  realized_pnl_usdc: string;
  total_fees_paid: string;
  total_volume: string;
  fill_count: number;
  volatility_regime: string | null;
  spread_regime: string | null;
  volume_regime: string | null;
  btc_trend_regime: string | null;
}

export interface PolymarketSessionListResponse {
  sessions: PolymarketSessionRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface PolymarketOrderRow {
  order_id: string;
  session_id: string;
  clob_order_id: string;
  token_id: string;
  side: string;
  price: string;
  size: string;
  status: string;
  placed_at: string;
  cancelled_at: string | null;
  post_only: boolean;
}

export interface PolymarketFillRow {
  fill_id: string;
  order_id: string;
  session_id: string;
  price: string;
  size: string;
  side: string;
  filled_at: string;
  fee_paid: string;
  midpoint_at_fill: string | null;
  midpoint_5s_after: string | null;
  midpoint_10s_after: string | null;
  adverse_selection_flag: boolean | null;
}

/** Regime + allocation — loose JSON-friendly shapes. */
export type JsonObject = Record<string, unknown>;

export interface SimulationRunBody {
  strategy_id: string;
  market_id: string;
  token_id: string;
  start: string;
  end: string;
  config?: Record<string, unknown>;
}

export interface SimulationRunAccepted {
  run_id: string;
  status: string;
}

export interface RegimeStateDto {
  detected_at: string;
  market_id?: string | null;
  primary_regime: string;
  regime_probabilities: Record<string, number>;
  quality: Record<string, unknown>;
  source: string;
}
