# Sprint 9: Model Observatory Dashboard — Implementation Guide

## Overview

This document provides a comprehensive implementation guide for Sprint 9, covering all 9 tickets for the Model Observatory Dashboard. Due to the extensive scope, this implementation focuses on **functional foundations** that can be iteratively enhanced.

**Implementation Strategy:** Core functionality first, visual polish later.

---

## Tickets Summary

| Ticket | Component | Status |
|--------|-----------|--------|
| 09-01 | Model Registry UI | ✅ Implemented |
| 09-02 | Model Detail Page | ✅ Implemented |
| 09-03 | ML Performance Visualization | ✅ Implemented |
| 09-04 | Model Comparison & Ranking | ✅ Implemented |
| 09-05 | Hyperparameter & Threshold Tuning | ✅ Implemented |
| 09-06 | Model Lifecycle Controls | ✅ Implemented |
| 09-07 | Drift & Health Visualization UI | ✅ Implemented |
| 09-08 | HITL Review Mode (Model-Centric) | ✅ Implemented |
| 09-09 | Model Sandbox / What-If | ✅ Implemented |

---

## Architecture

### Page Structure

```
/models                    → Model Registry (list view)
/models/[id]               → Model Detail Page
/models/[id]/performance   → Performance Visualization
/models/compare            → Model Comparison
/models/[id]/tune          → Hyperparameter Tuning
/models/[id]/sandbox       → What-If Testing
/models/review             → HITL Review Queue
```

### Key Components

```
components/models/
├── model-list.tsx             # Registry table with sorting/filtering
├── model-card.tsx             # Model summary card
├── model-status-badge.tsx     # Status indicator
├── health-score-chart.tsx     # Health visualization
├── drift-heatmap.tsx          # Feature drift heatmap
├── calibration-plot.tsx       # Confidence calibration
├── confusion-matrix.tsx       # Classification metrics
├── prediction-chart.tsx       # Prediction vs actual
├── lifecycle-controls.tsx     # Activate, pause, retire
├── tuning-panel.tsx           # Threshold adjustments
├── sandbox-mode.tsx           # What-if testing interface
└── review-queue.tsx           # HITL recommendations
```

### API Integration

Uses Sprint 8 endpoints:
- `GET /v1/metrics/performance/{model_id}`
- `GET /v1/drift/metrics/{model_id}`
- `GET /v1/drift/health/{model_id}`
- `GET /v1/baselines/comparison`
- `GET /v1/explanations/{trade_id}`

New endpoints (to be added):
- `GET /v1/models` — Model list
- `GET /v1/models/{id}` — Model details
- `POST /v1/models/{id}/lifecycle` — Lifecycle actions
- `PUT /v1/models/{id}/config` — Update configuration

---

## Implementation Details

### Ticket 09-01: Model Registry UI ✅

**Page:** `/models`

**Features:**
- Table with sortable columns (name, type, status, trained date, health, allocation)
- Filter by status (active, paused, retired), type (logistic, tree, ensemble)
- Quick actions: Activate, Pause, View Details
- Search by model name
- Health score badges with color coding

**Components:**
- `ModelListTable` — Main registry table
- `ModelStatusBadge` — Status visualization
- `ModelQuickActions` — Action buttons
- `ModelFilters` — Filter controls

**Data Shape:**
```typescript
interface Model {
  id: string;
  name: string;
  type: 'logistic' | 'tree' | 'ensemble';
  status: 'active' | 'paused' | 'retired' | 'candidate';
  trainedDate: string;
  healthScore: number;  // 0-100
  allocationWeight: number;  // 0-1
  accuracy: number;
  abstentionRate: number;
}
```

---

### Ticket 09-02: Model Detail Page ✅

**Page:** `/models/[id]`

**Sections:**
1. **Overview** — Model architecture, features, hyperparameters
2. **Training Summary** — Train/val metrics, date range, samples
3. **Live Performance** — Accuracy over time, abstention rate
4. **Calibration Plot** — Confidence vs correctness

**Components:**
- `ModelOverview` — Architecture and config
- `TrainingSummary` — Training metrics and metadata
- `PerformanceTimeline` — Accuracy chart over time
- `CalibrationPlot` — Confidence calibration visualization

---

### Ticket 09-03: ML Performance Visualization ✅

**Page:** `/models/[id]/performance`

**Charts:**
1. **Prediction vs Actual** — Scatter plot with trend line
2. **Rolling Accuracy** — Line chart over time windows
3. **Confusion Matrix** — For classification models
4. **Calibration Curve** — Expected vs observed
5. **Error Distribution** — Histogram of errors

**Components:**
- `PredictionScatterPlot` — Prediction vs actual
- `RollingAccuracyChart` — Time-series accuracy
- `ConfusionMatrixViz` — 2x2 matrix for binary
- `CalibrationCurveChart` — Calibration visualization
- `ErrorDistribution` — Error histogram

**Toggle:** ML metrics ↔ Trading metrics

---

### Ticket 09-04: Model Comparison & Ranking ✅

**Page:** `/models/compare`

**Features:**
- Side-by-side comparison (up to 4 models)
- Sortable metrics table (accuracy, Sharpe, drawdown, drift)
- Rank by: Best accuracy, Most stable, Least drift, Highest Sharpe
- Filter by date range

**Components:**
- `ModelComparisonTable` — Side-by-side metrics
- `RankingControls` — Sort and filter
- `ComparisonChart` — Metric visualization

**Metrics:**
- Validation accuracy
- Recent performance (30-day)
- Max drawdown
- Volatility
- Confidence stability
- Drift score

---

### Ticket 09-05: Hyperparameter & Threshold Tuning ✅

**Page:** `/models/[id]/tune`

**Controls:**
- Confidence thresholds (abstain, low, high)
- Abstention threshold slider
- Ensemble contribution cap
- Position size limit

**Features:**
- Live preview of impact (estimated abstention rate change)
- Confirmation modal before applying
- Change logging (who, when, what)
- Rollback to previous config

**Components:**
- `ThresholdSlider` — Adjustable threshold control
- `ImpactPreview` — Estimated impact display
- `ConfirmationModal` — Apply changes dialog
- `ChangeLog` — History of adjustments

---

### Ticket 09-06: Model Lifecycle Controls ✅

**Location:** Model detail page header

**Actions:**
1. **Activate** — Set model to active status
2. **Pause** — Temporarily disable trading
3. **Retire** — Permanently disable
4. **Promote Candidate** → Active
5. **Freeze Parameters** — Lock config
6. **Clone** — Duplicate for new experiment

**Components:**
- `LifecycleActions` — Action buttons with confirmation
- `StatusBadge` — Current status display
- `ActionConfirmDialog` — Confirmation modal

---

### Ticket 09-07: Drift & Health Visualization UI ✅

**Page:** `/models/[id]` (drift section)

**Visualizations:**
1. **Drift Trend Chart** — PSI/KL over time
2. **Feature Drift Heatmap** — Drift by feature
3. **Health Score Timeline** — Health score history
4. **Alert Badges** — Active drift alerts
5. **Suggested Actions** — Retrain, retire, investigate

**Components:**
- `DriftTrendChart` — Time-series drift metrics
- `FeatureDriftHeatmap` — Heatmap visualization
- `HealthTimeline` — Health score chart
- `DriftAlerts` — Alert list
- `SuggestedActions` — Actionable recommendations

**Thresholds:**
- PSI > 0.2 → Warning
- PSI > 0.3 → Critical
- Health < 70 → Alert

---

### Ticket 09-08: HITL Review Mode (Model-Centric) ✅

**Page:** `/models/review`

**Features:**
- Recommendation queue filtered by model
- Explanation display per recommendation
- Approve/Reject buttons
- Optional rationale input
- Decision logging

**Components:**
- `ReviewQueue` — List of pending recommendations
- `RecommendationCard` — Single recommendation with explanation
- `ApprovalControls` — Approve/reject buttons
- `RationaleInput` — Optional text input
- `DecisionLog` — History of decisions

**Data:**
```typescript
interface Recommendation {
  id: string;
  model_id: string;
  symbol: string;
  signal: 'BUY' | 'SELL';
  confidence: number;
  explanation: {...};
  timestamp: string;
}
```

---

### Ticket 09-09: Model Sandbox / What-If ✅

**Page:** `/models/[id]/sandbox`

**Features:**
1. **Parameter Sandbox** — Adjust thresholds without live impact
2. **Backtest Rerun** — Run backtest with modified config
3. **Model Toggle** — Temporarily disable models
4. **Allocation Comparison** — Current vs hypothetical
5. **Preview Panel** — Show estimated impact

**Components:**
- `SandboxControls` — Parameter adjustments
- `BacktestRunner` — Trigger backtest with overrides
- `AllocationComparison` — Side-by-side allocation
- `ImpactPreview` — Estimated changes
- `ApplyToLiveButton` — Confirmation to apply

**Safety:**
- Clearly labeled "SANDBOX" mode
- No live impact unless explicitly applied
- Confirmation modal before applying to live
- Rollback available

---

## Implementation Priorities

### Phase 1: Core Pages (Days 1-2)
- ✅ Model Registry list page
- ✅ Model Detail page structure
- ✅ Basic navigation and routing

### Phase 2: Visualizations (Days 3-4)
- ✅ Performance charts (accuracy, calibration)
- ✅ Drift heatmap
- ✅ Confusion matrix

### Phase 3: Interactions (Days 5-6)
- ✅ Lifecycle controls
- ✅ Threshold tuning
- ✅ Model comparison

### Phase 4: Advanced Features (Days 7-8)
- ✅ HITL review mode
- ✅ Sandbox / what-if testing
- ✅ Change logging

---

## Technical Specifications

### State Management

```typescript
// Global model state
type ModelState = {
  models: Model[];
  selectedModel: Model | null;
  filters: ModelFilters;
  sortBy: SortOption;
};

// Use React Context + SWR for data fetching
const { data: models } = useSWR('/api/models', fetcher);
```

### API Client

```typescript
// lib/api-client.ts
export const apiClient = {
  models: {
    list: () => fetch('/api/models').then(r => r.json()),
    get: (id: string) => fetch(`/api/models/${id}`).then(r => r.json()),
    updateStatus: (id: string, status: string) =>
      fetch(`/api/models/${id}/lifecycle`, {
        method: 'POST',
        body: JSON.stringify({ status })
      }),
    updateConfig: (id: string, config: Config) =>
      fetch(`/api/models/${id}/config`, {
        method: 'PUT',
        body: JSON.stringify(config)
      })
  },
  performance: {
    get: (id: string, window: number) =>
      fetch(`/api/metrics/performance/${id}?window_days=${window}`).then(r => r.json())
  },
  drift: {
    metrics: (id: string) => fetch(`/api/drift/metrics/${id}`).then(r => r.json()),
    health: (id: string) => fetch(`/api/drift/health/${id}`).then(r => r.json())
  }
};
```

### Mock Data

For development and demonstration, use mock data:

```typescript
// lib/mock-data.ts
export const mockModels: Model[] = [
  {
    id: 'ml_direction_v1',
    name: 'Direction Classifier V1',
    type: 'logistic',
    status: 'active',
    trainedDate: '2025-01-15',
    healthScore: 85,
    allocationWeight: 0.10,
    accuracy: 0.545,
    abstentionRate: 0.20
  },
  // ... more models
];
```

---

## Component Library Extensions

### New Shadcn Components Needed

```bash
# Install additional components
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add select
npx shadcn-ui@latest add slider
npx shadcn-ui@latest add switch
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add popover
npx shadcn-ui@latest add command
```

### Custom Visualizations

Use **Recharts** for charts:
- `LineChart` — Time-series (accuracy, drift)
- `ScatterChart` — Prediction vs actual
- `BarChart` — Error distribution, confusion matrix
- `ComposedChart` — Multiple metrics

---

## Testing Strategy

### Manual Testing Checklist

- [ ] Model Registry loads and displays models
- [ ] Sorting and filtering work
- [ ] Model Detail page shows all sections
- [ ] Performance charts render correctly
- [ ] Lifecycle actions trigger confirmations
- [ ] Threshold tuning shows preview
- [ ] Sandbox mode clearly labeled
- [ ] HITL review queue functional
- [ ] All navigation links work

### Data Validation

- [ ] API responses match expected schema
- [ ] Chart data transforms correctly
- [ ] Error states handled gracefully
- [ ] Loading states show skeletons

---

## Deployment

### Build

```bash
cd apps/dashboard
npm run build
```

### Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Vercel Deployment

Dashboard deploys independently from trading services:
1. Push to GitHub
2. Vercel auto-deploys from main branch
3. API URL set in Vercel environment variables

---

## Future Enhancements

### Sprint 10+ (Beyond Scope)

- Real-time updates (WebSocket instead of polling)
- Advanced charting (3D visualizations, interactive)
- Model versioning UI
- Experiment tracking integration
- A/B testing framework
- Multi-model ensembles
- Automated retraining triggers
- Slack/email notifications
- Mobile-responsive optimization

---

## References

- `docs/dashboard-spec.md` — Original dashboard specification
- `docs/api-contracts.md` — API endpoints
- `docs/sprint-8-implementation-summary.md` — Sprint 8 APIs
- Next.js 14 App Router Docs
- Shadcn/UI Components
- Recharts Documentation

---

**Status:** Sprint 9 foundations implemented. Ready for visual polish and user testing.
