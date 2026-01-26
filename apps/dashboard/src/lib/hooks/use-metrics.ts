"use client";

import useSWR from "swr";
import type { MetricsSummary, ApiResponse } from "../types";
import { fetchMetricsSummary } from "../api";

// Mock data for development
const mockMetrics: MetricsSummary = {
  total_pnl: "12345.67",
  total_pnl_percent: "15.23",
  sharpe_ratio: "1.85",
  max_drawdown: "-8.45",
  win_rate: "0.58",
  total_trades: 142,
  active_positions: 8,
  capital_deployed: "45000.00",
  available_capital: "55000.00",
  equity_curve: Array.from({ length: 30 }, (_, i) => ({
    date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000)
      .toISOString()
      .split("T")[0],
    value: (100000 + Math.random() * 15000 + i * 400).toFixed(2),
  })),
};

export function useMetrics(period: string = "1m") {
  const { data, error, isLoading, mutate } = useSWR<ApiResponse<MetricsSummary>>(
    `/metrics/summary?period=${period}`,
    () => fetchMetricsSummary(period),
    {
      refreshInterval: 5000,
      fallbackData: { data: mockMetrics },
      onError: () => {
        // Silently fail and use mock data
      },
    }
  );

  return {
    metrics: data?.data ?? mockMetrics,
    isLoading,
    isError: error,
    mutate,
  };
}
