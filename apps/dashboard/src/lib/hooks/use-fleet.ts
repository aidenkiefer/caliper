"use client";

import useSWR from "swr";
import { fetchFleetSignals, fetchFleetStatus, fetchPaperTrades } from "../api";
import type {
  FleetSignal,
  FleetStatus,
  PaperTrade,
} from "../types/models";
import { DEMO_MODE } from "../demo";

const now = Date.now();

const mockFleetStatus: FleetStatus = {
  generated_at: new Date(now).toISOString(),
  current_regime: "R1",
  current_mode: "paper",
  strategies: [
    {
      strategy_id: "poly_mm_v2",
      name: "Microstructure Maker v2",
      status: "active",
      mode: "paper",
      current_regime: "R1",
      pnl_24h_usd: 184.25,
      sharpe_7d: 1.72,
      fill_rate: 0.61,
      allocation_weight: 0.34,
      regime_alignment: 0.88,
      signal_count_24h: 148,
    },
    {
      strategy_id: "poly_directional_v1",
      name: "Directional Probability Model",
      status: "active",
      mode: "paper",
      current_regime: "R1",
      pnl_24h_usd: 92.4,
      sharpe_7d: 1.35,
      fill_rate: 0.54,
      allocation_weight: 0.24,
      regime_alignment: 0.79,
      signal_count_24h: 74,
    },
    {
      strategy_id: "poly_hybrid_v1",
      name: "Hybrid Maker/Directional",
      status: "cooldown",
      mode: "paper",
      current_regime: "R2",
      pnl_24h_usd: 141.75,
      sharpe_7d: 1.51,
      fill_rate: 0.58,
      allocation_weight: 0.24,
      regime_alignment: 0.83,
      signal_count_24h: 112,
    },
    {
      strategy_id: "poly_regime_v1",
      name: "Regime-Aware Model",
      status: "abstain",
      mode: "paper",
      current_regime: "R3",
      pnl_24h_usd: -12.8,
      sharpe_7d: 0.84,
      fill_rate: 0.29,
      allocation_weight: 0.18,
      regime_alignment: 0.63,
      signal_count_24h: 34,
    },
  ],
  regime_timeline: [
    {
      timestamp: new Date(now - 3 * 60 * 60 * 1000).toISOString(),
      regime: "R1",
      allocation_weights: {
        poly_mm_v2: 0.34,
        poly_directional_v1: 0.24,
        poly_hybrid_v1: 0.24,
        poly_regime_v1: 0.18,
      },
    },
    {
      timestamp: new Date(now - 2 * 60 * 60 * 1000).toISOString(),
      regime: "R1",
      allocation_weights: {
        poly_mm_v2: 0.33,
        poly_directional_v1: 0.24,
        poly_hybrid_v1: 0.25,
        poly_regime_v1: 0.18,
      },
    },
    {
      timestamp: new Date(now - 60 * 60 * 1000).toISOString(),
      regime: "R2",
      allocation_weights: {
        poly_mm_v2: 0.31,
        poly_directional_v1: 0.21,
        poly_hybrid_v1: 0.28,
        poly_regime_v1: 0.2,
      },
    },
    {
      timestamp: new Date(now).toISOString(),
      regime: "R1",
      allocation_weights: {
        poly_mm_v2: 0.34,
        poly_directional_v1: 0.24,
        poly_hybrid_v1: 0.24,
        poly_regime_v1: 0.18,
      },
    },
  ],
  comparison: [
    {
      strategy_id: "poly_mm_v2",
      baseline: "baseline_mm",
      sharpe_7d: 1.72,
      sortino_7d: 2.08,
      win_rate: 0.59,
      max_drawdown: -0.062,
      profit_factor: 1.41,
    },
    {
      strategy_id: "poly_directional_v1",
      baseline: "baseline_directional",
      sharpe_7d: 1.35,
      sortino_7d: 1.87,
      win_rate: 0.56,
      max_drawdown: -0.071,
      profit_factor: 1.29,
    },
    {
      strategy_id: "poly_hybrid_v1",
      baseline: "baseline_hybrid",
      sharpe_7d: 1.51,
      sortino_7d: 2.01,
      win_rate: 0.57,
      max_drawdown: -0.055,
      profit_factor: 1.36,
    },
    {
      strategy_id: "poly_regime_v1",
      baseline: "baseline_regime",
      sharpe_7d: 0.84,
      sortino_7d: 1.12,
      win_rate: 0.49,
      max_drawdown: -0.098,
      profit_factor: 0.97,
    },
  ],
};

const mockSignals: FleetSignal[] = [
  {
    signal_id: "sig-001",
    timestamp: new Date(now - 4 * 60 * 1000).toISOString(),
    strategy_id: "poly_mm_v2",
    market_id: "btc-hourly-2026-04-06-09",
    signal_type: "MARKET_MAKING",
    direction: "none",
    confidence: 0.91,
    action_taken: "executed",
    fill_price: null,
    regime: "R1",
  },
  {
    signal_id: "sig-002",
    timestamp: new Date(now - 3 * 60 * 1000).toISOString(),
    strategy_id: "poly_directional_v1",
    market_id: "btc-hourly-2026-04-06-10",
    signal_type: "DIRECTIONAL",
    direction: "long",
    confidence: 0.78,
    action_taken: "executed",
    fill_price: 0.54,
    regime: "R1",
  },
  {
    signal_id: "sig-003",
    timestamp: new Date(now - 2 * 60 * 1000).toISOString(),
    strategy_id: "poly_hybrid_v1",
    market_id: "btc-hourly-2026-04-06-08",
    signal_type: "HYBRID",
    direction: "long",
    confidence: 0.83,
    action_taken: "cancelled",
    fill_price: null,
    regime: "R2",
  },
  {
    signal_id: "sig-004",
    timestamp: new Date(now - 1 * 60 * 1000).toISOString(),
    strategy_id: "poly_regime_v1",
    market_id: "btc-hourly-2026-04-06-11",
    signal_type: "DIRECTIONAL",
    direction: "abstain",
    confidence: 0.32,
    action_taken: "abstained",
    fill_price: null,
    regime: "R3",
  },
];

const mockPaperTrades: PaperTrade[] = [
  {
    trade_id: "trade-001",
    executed_at: new Date(now - 6 * 60 * 1000).toISOString(),
    strategy_id: "poly_mm_v2",
    market_id: "btc-hourly-2026-04-06-09",
    side: "BUY",
    price: 0.53,
    quantity: 120,
    notional: 63.6,
    confidence: 0.91,
    status: "paper_filled",
    regime: "R1",
    allocation_weight: 0.34,
  },
  {
    trade_id: "trade-002",
    executed_at: new Date(now - 5 * 60 * 1000).toISOString(),
    strategy_id: "poly_directional_v1",
    market_id: "btc-hourly-2026-04-06-10",
    side: "BUY",
    price: 0.54,
    quantity: 80,
    notional: 43.2,
    confidence: 0.78,
    status: "paper_filled",
    regime: "R1",
    allocation_weight: 0.24,
  },
  {
    trade_id: "trade-003",
    executed_at: new Date(now - 4 * 60 * 1000).toISOString(),
    strategy_id: "poly_hybrid_v1",
    market_id: "btc-hourly-2026-04-06-08",
    side: "SELL",
    price: 0.49,
    quantity: 60,
    notional: 29.4,
    confidence: 0.83,
    status: "paper_filled",
    regime: "R2",
    allocation_weight: 0.24,
  },
];

export function useFleetStatus() {
  const { data, error, isLoading, mutate } = useSWR<FleetStatus>(
    "/fleet/status",
    fetchFleetStatus,
    {
      refreshInterval: 15000,
      ...(DEMO_MODE ? { fallbackData: mockFleetStatus } : {}),
    }
  );

  return {
    fleetStatus: data ?? (DEMO_MODE ? mockFleetStatus : null),
    isLoading,
    isError: error,
    mutate,
    isDemo: DEMO_MODE,
  };
}

export function useFleetSignals(limit: number = 50) {
  const { data, error, isLoading, mutate } = useSWR<FleetSignal[]>(
    ["/fleet/signals", limit],
    () => fetchFleetSignals({ limit }),
    {
      refreshInterval: 10000,
      ...(DEMO_MODE ? { fallbackData: mockSignals.slice(0, limit) } : {}),
    }
  );

  return {
    signals: data ?? (DEMO_MODE ? mockSignals.slice(0, limit) : []),
    isLoading,
    isError: error,
    mutate,
    isDemo: DEMO_MODE,
  };
}

export function usePaperTrades(limit: number = 50) {
  const { data, error, isLoading, mutate } = useSWR<PaperTrade[]>(
    ["/fleet/paper-trades", limit],
    () => fetchPaperTrades({ limit }),
    {
      refreshInterval: 15000,
      ...(DEMO_MODE ? { fallbackData: mockPaperTrades.slice(0, limit) } : {}),
    }
  );

  return {
    paperTrades: data ?? (DEMO_MODE ? mockPaperTrades.slice(0, limit) : []),
    isLoading,
    isError: error,
    mutate,
    isDemo: DEMO_MODE,
  };
}
