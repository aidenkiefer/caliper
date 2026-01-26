"use client";

import useSWR from "swr";
import type { Alert, PaginatedResponse } from "../types";
import { fetchAlerts } from "../api";

// Mock data for development
const mockAlerts: Alert[] = [
  {
    alert_id: "alert-001",
    severity: "WARNING",
    message: "Strategy 'Momentum V1' approaching max drawdown threshold (-8.5% of -10%)",
    context: {
      strategy_id: "momentum_v1",
      current_drawdown: "-8.5",
      threshold: "-10.0",
    },
    acknowledged: false,
    created_at: "2026-01-25T18:30:00Z",
  },
  {
    alert_id: "alert-002",
    severity: "INFO",
    message: "Daily P&L target reached: +$500",
    context: {
      daily_pnl: "523.45",
      target: "500.00",
    },
    acknowledged: true,
    created_at: "2026-01-25T16:00:00Z",
  },
  {
    alert_id: "alert-003",
    severity: "ERROR",
    message: "Data feed connection lost for 15 seconds",
    context: {
      provider: "alpaca",
      duration_seconds: 15,
    },
    acknowledged: false,
    created_at: "2026-01-25T14:22:00Z",
  },
];

export function useAlerts(params?: {
  severity?: string;
  acknowledged?: boolean;
  page?: number;
  per_page?: number;
}) {
  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<Alert>>(
    ["/alerts", params],
    () => fetchAlerts(params),
    {
      refreshInterval: 5000,
      fallbackData: {
        data: mockAlerts,
        meta: { total_count: mockAlerts.length, page: 1, per_page: 20 },
      },
      onError: () => {
        // Silently fail and use mock data
      },
    }
  );

  return {
    alerts: data?.data ?? mockAlerts,
    total: data?.meta?.total_count ?? mockAlerts.length,
    isLoading,
    isError: error,
    mutate,
  };
}
