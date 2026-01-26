"use client";

import useSWR from "swr";
import type { HealthStatus } from "../types";
import { fetchHealth } from "../api";

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
      fallbackData: mockHealth,
      onError: () => {
        // Silently fail and use mock data
      },
    }
  );

  return {
    health: data ?? mockHealth,
    isLoading,
    isError: error,
    mutate,
  };
}
