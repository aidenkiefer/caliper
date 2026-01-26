"use client";

import useSWR from "swr";
import type { Run, RunDetail, PaginatedResponse, ApiResponse } from "../types";
import { fetchRuns, fetchRun } from "../api";

// Mock data for development
const mockRuns: Run[] = [
  {
    run_id: "run-001",
    strategy_id: "momentum_v1",
    run_type: "BACKTEST",
    start_date: "2024-01-01",
    end_date: "2025-12-31",
    total_return: "18.45",
    sharpe_ratio: "2.15",
    max_drawdown: "-9.23",
    total_trades: 87,
    status: "COMPLETED",
    created_at: "2026-01-24T12:00:00Z",
    completed_at: "2026-01-24T12:15:30Z",
  },
  {
    run_id: "run-002",
    strategy_id: "mean_reversion_v1",
    run_type: "BACKTEST",
    start_date: "2024-06-01",
    end_date: "2025-06-01",
    total_return: "12.30",
    sharpe_ratio: "1.85",
    max_drawdown: "-7.45",
    total_trades: 65,
    status: "COMPLETED",
    created_at: "2026-01-23T14:00:00Z",
    completed_at: "2026-01-23T14:12:00Z",
  },
  {
    run_id: "run-003",
    strategy_id: "sma_crossover_v1",
    run_type: "BACKTEST",
    start_date: "2025-01-01",
    end_date: "2025-12-31",
    total_return: "-2.15",
    sharpe_ratio: "0.45",
    max_drawdown: "-15.67",
    total_trades: 42,
    status: "COMPLETED",
    created_at: "2026-01-22T09:00:00Z",
    completed_at: "2026-01-22T09:08:00Z",
  },
  {
    run_id: "run-004",
    strategy_id: "momentum_v1",
    run_type: "PAPER",
    start_date: "2026-01-01",
    end_date: "2026-01-25",
    total_return: "3.25",
    sharpe_ratio: "2.45",
    max_drawdown: "-2.10",
    total_trades: 15,
    status: "RUNNING",
    created_at: "2026-01-01T00:00:00Z",
  },
];

const mockRunDetail: RunDetail = {
  ...mockRuns[0],
  metrics: {
    total_return: "18.45",
    cagr: "17.82",
    sharpe_ratio: "2.15",
    sortino_ratio: "2.87",
    max_drawdown: "-9.23",
    win_rate: "0.61",
    profit_factor: "2.34",
    total_trades: 87,
    avg_trade_duration_hours: "72.50",
  },
  equity_curve: Array.from({ length: 250 }, (_, i) => ({
    date: new Date(2024, 0, 1 + i).toISOString().split("T")[0],
    value: (100000 + Math.random() * 5000 + i * 75).toFixed(2),
  })),
  trades: [
    {
      trade_id: "trade-001",
      symbol: "AAPL",
      side: "BUY",
      quantity: "100",
      entry_price: "150.25",
      exit_price: "158.50",
      pnl: "825.00",
      pnl_pct: "5.49",
      entry_time: "2024-01-15T10:30:00Z",
      exit_time: "2024-01-22T14:45:00Z",
    },
    {
      trade_id: "trade-002",
      symbol: "MSFT",
      side: "BUY",
      quantity: "50",
      entry_price: "380.00",
      exit_price: "372.50",
      pnl: "-375.00",
      pnl_pct: "-1.97",
      entry_time: "2024-01-20T09:30:00Z",
      exit_time: "2024-01-25T15:30:00Z",
    },
    {
      trade_id: "trade-003",
      symbol: "NVDA",
      side: "BUY",
      quantity: "25",
      entry_price: "480.00",
      exit_price: "525.00",
      pnl: "1125.00",
      pnl_pct: "9.38",
      entry_time: "2024-02-01T11:00:00Z",
      exit_time: "2024-02-15T14:00:00Z",
    },
  ],
};

export function useRuns(params?: {
  strategy_id?: string;
  run_type?: string;
  status?: string;
  page?: number;
  per_page?: number;
}) {
  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<Run>>(
    ["/runs", params],
    () => fetchRuns(params),
    {
      refreshInterval: 10000,
      fallbackData: {
        data: mockRuns,
        meta: { total_count: mockRuns.length, page: 1, per_page: 20 },
      },
      onError: () => {
        // Silently fail and use mock data
      },
    }
  );

  return {
    runs: data?.data ?? mockRuns,
    total: data?.meta?.total_count ?? mockRuns.length,
    isLoading,
    isError: error,
    mutate,
  };
}

export function useRun(runId: string) {
  const { data, error, isLoading, mutate } = useSWR<ApiResponse<RunDetail>>(
    runId ? `/runs/${runId}` : null,
    () => fetchRun(runId),
    {
      fallbackData: { data: mockRunDetail },
      onError: () => {
        // Silently fail and use mock data
      },
    }
  );

  return {
    run: data?.data ?? mockRunDetail,
    isLoading,
    isError: error,
    mutate,
  };
}
