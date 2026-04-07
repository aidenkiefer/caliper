import type { Recommendation } from "../types/models";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

export async function listPendingRecommendations(params?: {
  strategy_id?: string;
}): Promise<Recommendation[]> {
  const sp = new URLSearchParams();
  if (params?.strategy_id) sp.set("strategy_id", params.strategy_id);
  const q = sp.toString();
  const res = await fetch(`${API_BASE}/recommendations${q ? `?${q}` : ""}`);
  if (!res.ok) throw new Error("Failed to fetch recommendations");
  return res.json();
}

export async function approveRecommendation(
  recommendationId: string,
  body: { user_id: string; rationale?: string }
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/recommendations/${encodeURIComponent(recommendationId)}/approve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) throw new Error("Failed to approve recommendation");
}

export async function rejectRecommendation(
  recommendationId: string,
  body: { user_id: string; reason: string }
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/recommendations/${encodeURIComponent(recommendationId)}/reject`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) throw new Error("Failed to reject recommendation");
}

export async function fetchHitlStats(strategyId: string): Promise<{
  strategy_id: string;
  total_recommendations: number;
  approved: number;
  rejected: number;
  agreement_rate: number;
  pending: number;
}> {
  const res = await fetch(
    `${API_BASE}/recommendations/stats?strategy_id=${encodeURIComponent(strategyId)}`
  );
  if (!res.ok) throw new Error("Failed to fetch HITL stats");
  return res.json();
}

