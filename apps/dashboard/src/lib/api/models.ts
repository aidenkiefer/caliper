/**
 * API client for Model Observatory (Sprint 9)
 */

import type { Model, PerformanceMetrics, DriftMetrics, HealthScore, BaselineComparison, ModelConfig } from '../types/models';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// API client functions
export const modelsAPI = {
  /**
   * Get list of all models
   */
  list: async (): Promise<Model[]> => {
    // Mock data for now - replace with actual API when available
    return [
      {
        id: 'ml_direction_v1',
        name: 'Direction Classifier V1',
        type: 'logistic',
        status: 'active',
        trainedDate: '2025-01-15',
        healthScore: 85,
        allocationWeight: 0.10,
        accuracy: 0.545,
        abstentionRate: 0.20,
        metadata: {
          features: 34,
          samples: 1250,
          trainingPeriod: ['2020-01-01', '2025-01-01'],
          modelType: 'LogisticRegression'
        }
      },
      {
        id: 'ml_momentum_v1',
        name: 'Momentum Predictor V1',
        type: 'tree',
        status: 'candidate',
        trainedDate: '2025-01-20',
        healthScore: 78,
        allocationWeight: 0.0,
        accuracy: 0.521,
        abstentionRate: 0.15,
        metadata: {
          features: 34,
          samples: 1250,
          trainingPeriod: ['2020-01-01', '2025-01-01'],
          modelType: 'RandomForest'
        }
      }
    ];
  },

  /**
   * Get model by ID
   */
  get: async (id: string): Promise<Model> => {
    const models = await modelsAPI.list();
    const model = models.find(m => m.id === id);
    if (!model) throw new Error(`Model ${id} not found`);
    return model;
  },

  /**
   * Update model status (lifecycle action)
   */
  updateStatus: async (id: string, status: string): Promise<void> => {
    // TODO: Implement actual API call
    console.log(`Update model ${id} status to ${status}`);
  },

  /**
   * Update model configuration
   */
  updateConfig: async (id: string, config: Partial<ModelConfig>): Promise<void> => {
    // TODO: Implement actual API call
    console.log(`Update model ${id} config:`, config);
  }
};

export const performanceAPI = {
  /**
   * Get performance metrics for a model
   */
  get: async (modelId: string, windowDays: number = 30): Promise<PerformanceMetrics> => {
    const res = await fetch(`${API_BASE}/v1/metrics/performance/${modelId}?window_days=${windowDays}`);
    if (!res.ok) throw new Error('Failed to fetch performance metrics');
    return res.json();
  }
};

export const driftAPI = {
  /**
   * Get drift metrics for a model
   */
  metrics: async (modelId: string): Promise<DriftMetrics> => {
    const res = await fetch(`${API_BASE}/v1/drift/metrics/${modelId}`);
    if (!res.ok) throw new Error('Failed to fetch drift metrics');
    return res.json();
  },

  /**
   * Get health score for a model
   */
  health: async (modelId: string): Promise<HealthScore> => {
    const res = await fetch(`${API_BASE}/v1/drift/health/${modelId}`);
    if (!res.ok) throw new Error('Failed to fetch health score');
    return res.json();
  }
};

export const baselinesAPI = {
  /**
   * Get baseline comparison
   */
  comparison: async (): Promise<BaselineComparison> => {
    const res = await fetch(`${API_BASE}/v1/baselines/comparison`);
    if (!res.ok) throw new Error('Failed to fetch baseline comparison');
    return res.json();
  }
};
