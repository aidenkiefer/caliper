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
import type {
  FleetSignal,
  FleetStatus,
  PaperTrade,
  RankedUniverse,
} from "./types/models";
import type { FeatureSnapshot } from "./types/features";
import type {
  PolymarketSessionListResponse,
  PolymarketSessionRow,
  PolymarketOrderRow,
  PolymarketFillRow,
  SimulationRunBody,
  SimulationRunAccepted,
  RegimeStateDto,
} from "./types/explorers";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

/** Explorer fetches — throws ApiHttpError on non-2xx. */
async function fetchJson<T>(endpoint: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new ApiHttpError(res.status, detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export class ApiHttpError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiHttpError";
    this.status = status;
  }
}

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

// Paper portfolio (Phase 1 MTM wiring)
export async function createPaperAllocation(data: {
  strategy_id: string;
  amount_usd: string;
  note?: string;
}): Promise<{ allocation_id: number }> {
  return fetchApi("/paper/allocations", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function createEquityFill(data: {
  strategy_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: string;
  price: string;
  fees_usd?: string;
  venue?: string;
  client_order_id?: string;
  broker_order_id?: string;
  metadata?: Record<string, unknown>;
}): Promise<{ fill_id: string }> {
  return fetchApi("/paper/equity-fills", {
    method: "POST",
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

// Sprint 16: Cross-sectional ranking + fleet (fetchJson → ApiHttpError on failure)
export async function fetchRankedUniverse(): Promise<RankedUniverse> {
  return fetchJson("/ranking/current");
}

export async function fetchFleetStatus(): Promise<FleetStatus> {
  return fetchJson("/fleet/status");
}

export async function fetchFleetSignals(params?: {
  limit?: number;
}): Promise<FleetSignal[]> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  const query = searchParams.toString();
  return fetchJson(`/fleet/signals${query ? `?${query}` : ""}`);
}

// Sprint 12 — feature snapshots (requires API DB_URL)
export async function fetchFeatureLatest(
  marketId: string
): Promise<FeatureSnapshot> {
  const encoded = encodeURIComponent(marketId);
  const res = await fetch(`${API_URL}/features/${encoded}/latest`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new ApiHttpError(res.status, detail || res.statusText);
  }
  return res.json();
}

export async function fetchFeatureHistory(
  marketId: string,
  params: { start: string; end: string; limit?: number }
): Promise<FeatureSnapshot[]> {
  const encoded = encodeURIComponent(marketId);
  const searchParams = new URLSearchParams();
  searchParams.set("start", params.start);
  searchParams.set("end", params.end);
  if (params.limit != null) {
    searchParams.set("limit", String(params.limit));
  }
  const res = await fetch(
    `${API_URL}/features/${encoded}/history?${searchParams.toString()}`,
    { headers: { "Content-Type": "application/json" } }
  );
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new ApiHttpError(res.status, detail || res.statusText);
  }
  return res.json();
}

export async function fetchPaperTrades(params?: {
  start?: string;
  end?: string;
  strategy_id?: string;
  market_id?: string;
  limit?: number;
}): Promise<PaperTrade[]> {
  const searchParams = new URLSearchParams();
  if (params?.start) searchParams.set("start", params.start);
  if (params?.end) searchParams.set("end", params.end);
  if (params?.strategy_id) searchParams.set("strategy_id", params.strategy_id);
  if (params?.market_id) searchParams.set("market_id", params.market_id);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  const query = searchParams.toString();
  return fetchJson(`/fleet/paper-trades${query ? `?${query}` : ""}`);
}

// --- Polymarket sessions (Sprint 10) ---

export async function listPolymarketSessions(params?: {
  status?: string;
  regime?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}): Promise<PolymarketSessionListResponse> {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.regime) sp.set("regime", params.regime);
  if (params?.start_date) sp.set("start_date", params.start_date);
  if (params?.end_date) sp.set("end_date", params.end_date);
  if (params?.page != null) sp.set("page", String(params.page));
  if (params?.page_size != null) sp.set("page_size", String(params.page_size));
  const q = sp.toString();
  return fetchJson(`/polymarket/sessions${q ? `?${q}` : ""}`);
}

export async function getPolymarketSession(
  sessionId: string
): Promise<PolymarketSessionRow> {
  return fetchJson(`/polymarket/sessions/${encodeURIComponent(sessionId)}`);
}

export async function listPolymarketSessionOrders(
  sessionId: string,
  status?: string
): Promise<PolymarketOrderRow[]> {
  const sp = new URLSearchParams();
  if (status) sp.set("status", status);
  const q = sp.toString();
  return fetchJson(
    `/polymarket/sessions/${encodeURIComponent(sessionId)}/orders${q ? `?${q}` : ""}`
  );
}

export async function listPolymarketSessionFills(
  sessionId: string,
  adverse_only?: boolean
): Promise<PolymarketFillRow[]> {
  const sp = new URLSearchParams();
  if (adverse_only === true) sp.set("adverse_only", "true");
  const q = sp.toString();
  return fetchJson(
    `/polymarket/sessions/${encodeURIComponent(sessionId)}/fills${q ? `?${q}` : ""}`
  );
}

// --- Regime + allocation (Sprint 15) ---

export async function fetchRegimeCurrent(): Promise<RegimeStateDto> {
  return fetchJson("/regime/current");
}

export async function fetchRegimeCurrentForMarket(
  marketId: string
): Promise<RegimeStateDto> {
  return fetchJson(`/regime/${encodeURIComponent(marketId)}/current`);
}

export async function fetchRegimeHistory(params: {
  start: string;
  end: string;
  market_id?: string;
  limit?: number;
}): Promise<RegimeStateDto[]> {
  const sp = new URLSearchParams();
  sp.set("start", params.start);
  sp.set("end", params.end);
  if (params.market_id) sp.set("market_id", params.market_id);
  if (params.limit != null) sp.set("limit", String(params.limit));
  return fetchJson(`/regime/history?${sp.toString()}`);
}

export async function fetchAllocationCurrent(): Promise<unknown> {
  return fetchJson("/allocation/current");
}

export async function fetchAllocationHistory(params: {
  start: string;
  end: string;
  limit?: number;
}): Promise<unknown[]> {
  const sp = new URLSearchParams();
  sp.set("start", params.start);
  sp.set("end", params.end);
  if (params.limit != null) sp.set("limit", String(params.limit));
  return fetchJson(`/allocation/history?${sp.toString()}`);
}

export async function fetchPerformanceMatrix(): Promise<unknown> {
  return fetchJson("/allocation/performance-matrix");
}

// --- Probability (Sprint 14) ---

export async function fetchProbabilityCalibration(
  modelVersion?: string
): Promise<unknown> {
  const sp = new URLSearchParams();
  if (modelVersion) sp.set("model_version", modelVersion);
  const q = sp.toString();
  return fetchJson(`/probability/calibration${q ? `?${q}` : ""}`);
}

export async function fetchProbabilityLagTests(
  type = "cross_correlation"
): Promise<unknown> {
  return fetchJson(`/probability/lag-tests?type=${encodeURIComponent(type)}`);
}

export async function fetchProbabilityLatest(marketId: string): Promise<unknown> {
  return fetchJson(
    `/probability/${encodeURIComponent(marketId)}/latest`
  );
}

export async function fetchProbabilityHistory(
  marketId: string,
  params?: { start?: string; end?: string }
): Promise<unknown[]> {
  const sp = new URLSearchParams();
  if (params?.start) sp.set("start", params.start);
  if (params?.end) sp.set("end", params.end);
  const q = sp.toString();
  return fetchJson(
    `/probability/${encodeURIComponent(marketId)}/history${q ? `?${q}` : ""}`
  );
}

export async function postProbabilityTrain(body: {
  market_id: string;
  model_type: string;
  start: string;
  end: string;
}): Promise<SimulationRunAccepted> {
  return fetchJson("/probability/train", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// --- Simulation + evaluation (Sprint 13) ---

export async function postSimulationRun(
  body: SimulationRunBody
): Promise<SimulationRunAccepted> {
  return fetchJson("/simulation/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchSimulationResult(runId: string): Promise<unknown> {
  return fetchJson(`/simulation/${encodeURIComponent(runId)}/result`);
}

export async function fetchEvaluationCompare(
  strategyIds: string[]
): Promise<unknown> {
  const ids = strategyIds.map((s) => s.trim()).filter(Boolean).join(",");
  return fetchJson(
    `/evaluation/compare?strategy_ids=${encodeURIComponent(ids)}`
  );
}

export async function fetchEvaluationLatest(strategyId: string): Promise<unknown> {
  return fetchJson(
    `/evaluation/${encodeURIComponent(strategyId)}/latest`
  );
}

export async function fetchEvaluationRegimes(
  strategyId: string
): Promise<unknown[]> {
  return fetchJson(
    `/evaluation/${encodeURIComponent(strategyId)}/regimes`
  );
}
