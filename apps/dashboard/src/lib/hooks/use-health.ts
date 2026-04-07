"use client";

import useSWR from "swr";
import type { HealthStatus } from "../types";
import { fetchHealth } from "../api";
import { DEMO_MODE } from "../demo";

// Mock data for development
const mockHealth: HealthStatus = {
  status: "healthy",
  services: {
    database: {
      status: "healthy",
      latency_ms: 12,
    },
    data_feed: {
      status: "healthy",
      last_update: "2026-01-25T22:34:50Z",
      staleness_seconds: 10,
    },
    broker_connection: {
      status: "healthy",
      broker: "alpaca",
      mode: "PAPER",
    },
    redis: {
      status: "healthy",
    },
  },
  timestamp: new Date().toISOString(),
};

export function useHealth() {
  const { data, error, isLoading, mutate } = useSWR<HealthStatus>(
    "/health",
    fetchHealth,
    {
      refreshInterval: 10000,
      ...(DEMO_MODE ? { fallbackData: mockHealth } : {}),
    }
  );

  return {
    health: data ?? (DEMO_MODE ? mockHealth : null),
    isLoading,
    isError: error,
    mutate,
    isDemo: DEMO_MODE,
  };
}
