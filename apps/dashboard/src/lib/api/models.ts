/**
 * API client for Model Observatory (Sprint 9)
 */

import type { Model, PerformanceMetrics, DriftMetrics, HealthScore, BaselineComparison, ModelConfig } from '../types/models';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1';

// API client functions
export const modelsAPI = {
  /**
   * Get list of all models
   */
  list: async (): Promise<Model[]> => {
    const res = await fetch(`${API_BASE}/models`);
    if (!res.ok) throw new Error('Failed to fetch models');
    return res.json();
  },

  /**
   * Get model by ID
   */
  get: async (id: string): Promise<Model> => {
    const res = await fetch(`${API_BASE}/models/${encodeURIComponent(id)}`);
    if (!res.ok) throw new Error(`Model ${id} not found`);
    return res.json();
  },

  /**
   * Update model status (lifecycle action)
   */
  updateStatus: async (id: string, status: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/models/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error('Failed to update model status');
  },

  /**
   * Update model configuration
   */
  updateConfig: async (id: string, config: Partial<ModelConfig>): Promise<void> => {
    // TODO: implement once model config persistence exists in the API.
    void id;
    void config;
    throw new Error('Not implemented');
  }
};

export const performanceAPI = {
  /**
   * Get performance metrics for a model
   */
  get: async (modelId: string, windowDays: number = 30): Promise<PerformanceMetrics> => {
    const res = await fetch(`${API_BASE}/metrics/performance/${encodeURIComponent(modelId)}?window_days=${windowDays}`);
    if (!res.ok) throw new Error('Failed to fetch performance metrics');
    return res.json();
  }
};

export const driftAPI = {
  /**
   * Get drift metrics for a model
   */
  metrics: async (modelId: string): Promise<DriftMetrics> => {
    const res = await fetch(`${API_BASE}/drift/metrics/${encodeURIComponent(modelId)}`);
    if (!res.ok) throw new Error('Failed to fetch drift metrics');
    return res.json();
  },

  /**
   * Get health score for a model
   */
  health: async (modelId: string): Promise<HealthScore> => {
    const res = await fetch(`${API_BASE}/drift/health/${encodeURIComponent(modelId)}`);
    if (!res.ok) throw new Error('Failed to fetch health score');
    return res.json();
  }
};

export const baselinesAPI = {
  /**
   * Get baseline comparison
   */
  comparison: async (strategyId: string): Promise<BaselineComparison> => {
    const res = await fetch(`${API_BASE}/baselines/comparison?strategy_id=${encodeURIComponent(strategyId)}`);
    if (!res.ok) throw new Error('Failed to fetch baseline comparison');
    return res.json();
  }
};
