"use client";

import useSWR from "swr";
import { DEMO_MODE } from "../demo";

export interface StrategyPositionRow {
  surface: string;
  instrument_id: string;
  quantity: string;
  avg_cost: string;
  mark_price?: string | null;
  mark_source: string;
  market_value?: string | null;
  unrealized_pnl?: string | null;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

async function fetchStrategyPositions(strategyId: string): Promise<StrategyPositionRow[]> {
  const res = await fetch(`${API_URL}/strategies/${encodeURIComponent(strategyId)}/positions`);
  if (!res.ok) throw new Error("Failed to fetch strategy positions");
  return res.json();
}

export function usePositions(params?: { strategy_id?: string }) {
  const strategyId = params?.strategy_id;
  const { data, error, isLoading, mutate } = useSWR<StrategyPositionRow[]>(
    strategyId ? `/strategies/${strategyId}/positions` : null,
    () => fetchStrategyPositions(strategyId as string),
    {
      refreshInterval: 15000,
      ...(DEMO_MODE ? { fallbackData: [] } : {}),
    }
  );

  return {
    positions: data ?? [],
    isLoading,
    isError: error,
    mutate,
    isDemo: DEMO_MODE,
  };
}

