import type {
  MetricsSummary,
  Strategy,
  Position,
  Run,
  RunDetail,
  Alert,
  HealthStatus,
  ApiResponse,
  PaginatedResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

// Metrics
export async function fetchMetricsSummary(
  period: string = "1m"
): Promise<ApiResponse<MetricsSummary>> {
  return fetchApi(`/metrics/summary?period=${period}`);
}

// Strategies
export async function fetchStrategies(params?: {
  status?: string;
  mode?: string;
}): Promise<PaginatedResponse<Strategy>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.mode) searchParams.set("mode", params.mode);
  const query = searchParams.toString();
  return fetchApi(`/strategies${query ? `?${query}` : ""}`);
}

export async function fetchStrategy(
  strategyId: string
): Promise<ApiResponse<Strategy>> {
  return fetchApi(`/strategies/${strategyId}`);
}

export async function updateStrategy(
  strategyId: string,
  data: Partial<Strategy>
): Promise<ApiResponse<Strategy>> {
  return fetchApi(`/strategies/${strategyId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// Positions
export async function fetchPositions(params?: {
  strategy_id?: string;
  symbol?: string;
  mode?: string;
  page?: number;
  per_page?: number;
}): Promise<PaginatedResponse<Position>> {
  const searchParams = new URLSearchParams();
  if (params?.strategy_id) searchParams.set("strategy_id", params.strategy_id);
  if (params?.symbol) searchParams.set("symbol", params.symbol);
  if (params?.mode) searchParams.set("mode", params.mode);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.per_page) searchParams.set("per_page", params.per_page.toString());
  const query = searchParams.toString();
  return fetchApi(`/positions${query ? `?${query}` : ""}`);
}

// Runs
export async function fetchRuns(params?: {
  strategy_id?: string;
  run_type?: string;
  status?: string;
  page?: number;
  per_page?: number;
}): Promise<PaginatedResponse<Run>> {
  const searchParams = new URLSearchParams();
  if (params?.strategy_id) searchParams.set("strategy_id", params.strategy_id);
  if (params?.run_type) searchParams.set("run_type", params.run_type);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.per_page) searchParams.set("per_page", params.per_page.toString());
  const query = searchParams.toString();
  return fetchApi(`/runs${query ? `?${query}` : ""}`);
}

export async function fetchRun(runId: string): Promise<ApiResponse<RunDetail>> {
  return fetchApi(`/runs/${runId}`);
}

export async function createRun(data: {
  strategy_id: string;
  start_date: string;
  end_date: string;
  initial_capital: string;
}): Promise<ApiResponse<{ run_id: string; status: string }>> {
  return fetchApi("/runs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Alerts
export async function fetchAlerts(params?: {
  severity?: string;
  acknowledged?: boolean;
  page?: number;
  per_page?: number;
}): Promise<PaginatedResponse<Alert>> {
  const searchParams = new URLSearchParams();
  if (params?.severity) searchParams.set("severity", params.severity);
  if (params?.acknowledged !== undefined)
    searchParams.set("acknowledged", params.acknowledged.toString());
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.per_page) searchParams.set("per_page", params.per_page.toString());
  const query = searchParams.toString();
  return fetchApi(`/alerts${query ? `?${query}` : ""}`);
}

export async function acknowledgeAlert(
  alertId: string
): Promise<ApiResponse<Alert>> {
  return fetchApi(`/alerts/${alertId}/acknowledge`, {
    method: "PATCH",
  });
}

// Health
export async function fetchHealth(): Promise<HealthStatus> {
  return fetchApi("/health");
}

// Controls
export async function activateKillSwitch(data: {
  action: "activate" | "deactivate";
  strategy_id?: string;
  reason: string;
}): Promise<ApiResponse<{ kill_switch_active: boolean }>> {
  return fetchApi("/controls/kill-switch", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
