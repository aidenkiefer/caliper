"use client";

import useSWR from "swr";
import { fetchRankedUniverse } from "../api";
import type { RankedMarket, RankedUniverse } from "../types/models";
import { DEMO_MODE } from "../demo";

const now = Date.now();

const mockRankedMarkets: RankedMarket[] = [
  {
    market_id: "btc-hourly-2026-04-06-09",
    market_name: "BTC Hourly 09:00 UTC",
    condition_id: "cond_btc_0900",
    side: "YES",
    score: 0.92,
    ev_adj: 0.064,
    feasibility: 0.88,
    confidence: 0.81,
    spread_pct: 0.011,
    volume_24h_usd: 48250,
    time_to_close_seconds: 1740,
    selected: true,
    cooldown_protected: false,
  },
  {
    market_id: "btc-hourly-2026-04-06-10",
    market_name: "BTC Hourly 10:00 UTC",
    condition_id: "cond_btc_1000",
    side: "NO",
    score: 0.86,
    ev_adj: 0.051,
    feasibility: 0.84,
    confidence: 0.77,
    spread_pct: 0.013,
    volume_24h_usd: 36120,
    time_to_close_seconds: 3120,
    selected: true,
    cooldown_protected: false,
  },
  {
    market_id: "btc-hourly-2026-04-06-08",
    market_name: "BTC Hourly 08:00 UTC",
    condition_id: "cond_btc_0800",
    side: "YES",
    score: 0.74,
    ev_adj: 0.037,
    feasibility: 0.79,
    confidence: 0.72,
    spread_pct: 0.015,
    volume_24h_usd: 29510,
    time_to_close_seconds: 840,
    selected: true,
    cooldown_protected: true,
  },
  {
    market_id: "btc-hourly-2026-04-06-07",
    market_name: "BTC Hourly 07:00 UTC",
    condition_id: "cond_btc_0700",
    side: "YES",
    score: 0.31,
    ev_adj: 0.011,
    feasibility: 0.46,
    confidence: 0.55,
    spread_pct: 0.021,
    volume_24h_usd: 14820,
    time_to_close_seconds: 3840,
    selected: false,
    cooldown_protected: false,
  },
  {
    market_id: "btc-hourly-2026-04-06-11",
    market_name: "BTC Hourly 11:00 UTC",
    condition_id: "cond_btc_1100",
    side: "NO",
    score: 0.18,
    ev_adj: -0.012,
    feasibility: 0.19,
    confidence: 0.39,
    spread_pct: 0.032,
    volume_24h_usd: 9800,
    time_to_close_seconds: 4680,
    selected: false,
    cooldown_protected: false,
  },
];

const mockRankedUniverse: RankedUniverse = {
  ranked_at: new Date(now).toISOString(),
  total_candidates: mockRankedMarkets.length,
  selected_markets: mockRankedMarkets.filter((market) => market.selected),
  excluded_markets: ["btc-hourly-2026-04-06-11"],
  ranking_method: "ev_adj_plus_feasibility_v1",
  cooldown_protected: ["btc-hourly-2026-04-06-08"],
  candidate_markets: mockRankedMarkets,
};

export function useRankingUniverse() {
  const { data, error, isLoading, mutate } = useSWR<RankedUniverse>(
    "/ranking/current",
    fetchRankedUniverse,
    {
      refreshInterval: 15000,
      ...(DEMO_MODE ? { fallbackData: mockRankedUniverse } : {}),
    }
  );

  return {
    rankedUniverse: data ?? (DEMO_MODE ? mockRankedUniverse : null),
    isLoading,
    isError: error,
    mutate,
    isDemo: DEMO_MODE,
  };
}
