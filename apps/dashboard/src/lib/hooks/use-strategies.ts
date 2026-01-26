"use client";

import useSWR from "swr";
import type { Strategy, PaginatedResponse, ApiResponse } from "../types";
import { fetchStrategies, fetchStrategy } from "../api";

// Mock data for development
const mockStrategies: Strategy[] = [
  {
    strategy_id: "momentum_v1",
    name: "Momentum Strategy V1",
    description: "XGBoost-based momentum trading on S&P 500 stocks",
    status: "active",
    mode: "PAPER",
    universe_size: 50,
    max_positions: 10,
    risk_per_trade_pct: "1.5",
    created_at: "2026-01-15T10:00:00Z",
    updated_at: "2026-01-25T08:00:00Z",
    performance: {
      total_pnl: "2345.67",
      sharpe_ratio: "2.1",
      max_drawdown: "-5.2",
      win_rate: "0.62",
    },
  },
  {
    strategy_id: "mean_reversion_v1",
    name: "Mean Reversion Strategy",
    description: "Statistical arbitrage using mean reversion signals",
    status: "active",
    mode: "PAPER",
    universe_size: 30,
    max_positions: 5,
    risk_per_trade_pct: "2.0",
    created_at: "2026-01-10T10:00:00Z",
    updated_at: "2026-01-24T12:00:00Z",
    performance: {
      total_pnl: "1890.45",
      sharpe_ratio: "1.8",
      max_drawdown: "-6.1",
      win_rate: "0.55",
    },
  },
  {
    strategy_id: "sma_crossover_v1",
    name: "SMA Crossover",
    description: "Simple Moving Average crossover strategy",
    status: "inactive",
    mode: "BACKTEST",
    universe_size: 10,
    max_positions: 3,
    risk_per_trade_pct: "1.0",
    created_at: "2026-01-05T10:00:00Z",
    updated_at: "2026-01-20T15:00:00Z",
    performance: {
      total_pnl: "-245.30",
      sharpe_ratio: "0.8",
      max_drawdown: "-12.3",
      win_rate: "0.45",
    },
  },
];

export function useStrategies(params?: { status?: string; mode?: string }) {
  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<Strategy>>(
    ["/strategies", params],
    () => fetchStrategies(params),
    {
      refreshInterval: 10000,
      fallbackData: {
        data: mockStrategies,
        meta: { total_count: mockStrategies.length, page: 1, per_page: 20 },
      },
      onError: () => {
        // Silently fail and use mock data
      },
    }
  );

  return {
    strategies: data?.data ?? mockStrategies,
    total: data?.meta?.total_count ?? mockStrategies.length,
    isLoading,
    isError: error,
    mutate,
  };
}

export function useStrategy(strategyId: string) {
  const { data, error, isLoading, mutate } = useSWR<ApiResponse<Strategy>>(
    strategyId ? `/strategies/${strategyId}` : null,
    () => fetchStrategy(strategyId),
    {
      fallbackData: {
        data: mockStrategies.find((s) => s.strategy_id === strategyId) ?? mockStrategies[0],
      },
      onError: () => {
        // Silently fail and use mock data
      },
    }
  );

  return {
    strategy: data?.data ?? mockStrategies.find((s) => s.strategy_id === strategyId),
    isLoading,
    isError: error,
    mutate,
  };
}
