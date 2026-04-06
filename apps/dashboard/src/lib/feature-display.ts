import type { FeatureSnapshot } from "@/lib/types/features";

export interface FeatureFieldGroup {
  id: string;
  helpId: string;
  label: string;
  keys: (keyof FeatureSnapshot)[];
}

/** Sprint 12 four families + identity timing fields. */
export const FEATURE_FIELD_GROUPS: FeatureFieldGroup[] = [
  {
    id: "identity",
    helpId: "features-market-state",
    label: "Identity & timing",
    keys: [
      "market_id",
      "token_id",
      "captured_at",
      "time_to_close_seconds",
      "time_since_open_seconds",
    ],
  },
  {
    id: "market_state",
    helpId: "features-market-state",
    label: "Market state",
    keys: [
      "mid_price",
      "implied_probability",
      "spread",
      "spread_bps",
      "book_depth_bid_5tick",
      "book_depth_ask_5tick",
      "time_since_last_trade",
      "time_since_last_price_change",
    ],
  },
  {
    id: "microstructure",
    helpId: "features-microstructure",
    label: "Microstructure",
    keys: [
      "order_book_imbalance",
      "trade_flow_imbalance_1m",
      "trade_flow_imbalance_5m",
      "last_5min_volume_share",
      "aggressor_buy_fraction_1m",
      "vpin_proxy",
      "fee_rate_current",
      "reward_eligible",
      "reward_max_spread",
      "reward_min_size",
    ],
  },
  {
    id: "probabilistic",
    helpId: "features-probabilistic",
    label: "Probabilistic (BTC)",
    keys: [
      "btc_distance_to_open",
      "btc_rv_1m",
      "btc_rv_5m",
      "btc_rv_15m",
      "btc_momentum_5m",
      "btc_sign_persistence_5m",
      "btc_funding_rate",
      "btc_basis_proxy",
    ],
  },
  {
    id: "regime",
    helpId: "features-regime",
    label: "Regime",
    keys: [
      "vol_regime",
      "trend_regime",
      "time_bucket",
      "near_close_flag",
      "toxicity_regime",
      "spread_regime",
      "liquidity_score",
      "competitive_pressure",
      "data_staleness_flag",
    ],
  },
];

export function formatFeatureValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}
