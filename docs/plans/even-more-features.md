# Model Observatory & Control Plane Features

## Purpose
This sprint introduces a **model-centric observability and control layer** in the dashboard.

The goal is to make Caliper intuitive and powerful for users with:
- machine learning background
- software engineering mindset
- little to no trading/finance experience

Models should be treated as **inspectable, configurable, and comparable software artifacts**, not opaque trading strategies.

This sprint shifts the dashboard from “What trades happened?” to:
> “Why is this model behaving this way, and how should I adjust it?”

---

## Core Concept: Models as First-Class Entities

Each model in the ensemble should have:
- identity
- version history
- parameters
- performance metrics
- training / validation context
- lifecycle state (active, paused, retired)

The dashboard must expose these concepts directly.

---

## Feature 1: Model Registry UI (Single Source of Truth)

### Description
Add a dedicated **Model Registry** page to the dashboard.

This page lists all models known to the system.

### Displayed Information (per model)
- Model name / ID
- Model type (e.g. tree, linear, neural, heuristic)
- Status (active, paused, candidate, retired)
- Date trained
- Training dataset window
- Last evaluation timestamp
- Current allocation weight (if used)
- Health score (from drift / decay metrics)

### Why This Matters
This gives users a **mental map** of the system.
Without this, ensembles feel like magic.

### Deliverables
- Backend model registry API
- Persistent model metadata store
- Dashboard list view with sorting/filtering

---

## Feature 2: Individual Model Detail Page

### Description
Clicking a model opens a **Model Detail View**.

This is the core ML-focused interface.

### Sections

#### A) Model Overview
- Model architecture / class
- Feature set used
- Hyperparameters
- Training objective
- Reward / loss function

#### B) Training & Validation Summary
- Training period
- Validation method (walk-forward, sliding window, etc.)
- Validation metrics (accuracy, precision, recall, MAE, etc.)
- Overfitting indicators (train vs val gap)

#### C) Live / Paper Performance
- PnL (contextual, not primary)
- Prediction accuracy over time
- Confidence calibration plots
- Abstention rate

### Why This Matters
This lets users reason about **ML quality**, not just money.

---

## Feature 3: Performance Visualization (ML-First)

### Description
Add ML-native performance plots instead of only trading plots.

### Visualizations
- Prediction vs actual (directional or regression)
- Rolling accuracy
- Confusion matrix (for classification tasks)
- Calibration curves (confidence vs correctness)
- Error distributions

### Why This Matters
These are familiar tools for ML users and lower the barrier to entry dramatically.

### Deliverables
- Metrics computation layer
- Time-series + aggregate visualizations
- Toggle between ML metrics and trading metrics

---

## Feature 4: Hyperparameter & Threshold Tuning Interface

### Description
Allow **controlled parameter tweaking** from the dashboard.

This does NOT mean retraining arbitrarily in production.

### Allowed Adjustments
- Confidence thresholds
- Abstention thresholds
- Reward weighting (e.g. risk vs return emphasis)
- Ensemble contribution caps
- Allocation limits

### Guardrails
- Changes require confirmation
- Changes are logged
- Changes trigger re-evaluation / backtest
- Rollback supported

### Why This Matters
This turns the system into an **interactive ML lab**, not a black box.

---

## Feature 5: Model Comparison & Ranking View

### Description
Add a page to compare models side-by-side.

### Comparison Dimensions
- Validation metrics
- Recent performance
- Drawdown
- Volatility
- Confidence stability
- Drift score

### Sorting / Filtering
- Best recent performers
- Most stable
- Least risky
- Most confident

### Why This Matters
This is essential for ensemble reasoning and capital allocation.

---

## Feature 6: Experiment & Training Run Traceability

### Description
Link each model to the experiment that produced it.

### Display
- Dataset version
- Feature set version
- Hyperparameter config
- Training code reference (commit hash)
- Notes / rationale (optional)

### Why This Matters
This supports reproducibility and prevents “mystery models.”

---

## Feature 7: Model Lifecycle Controls

### Description
Expose lifecycle actions in the dashboard.

### Actions
- Activate / deactivate model
- Promote candidate → active
- Retire model
- Freeze parameters
- Clone model config for new experiment

### Why This Matters
This enables safe iteration and prevents accidental overuse of bad models.

---

## Feature 8: Model Drift & Health Visualization

### Description
Surface drift metrics visually on a per-model basis.

### Visuals
- Feature drift over time
- Confidence drift
- Error drift
- Health score trend

### Alerts
- Threshold crossings
- Suggested retraining
- Suggested retirement

### Why This Matters
Models should **age visibly**, not silently.

---

## Feature 9: Human-in-the-Loop Review Mode (Model-Centric)

### Description
Allow users to:
- review model recommendations
- see explanations
- approve or reject at the model level

### Logged Data
- Model recommendation
- Human action
- Rationale (optional)
- Outcome

### Why This Matters
This helps users build intuition and trust.

---

## Feature 10: Model Sandbox / “What-If” Testing

### Description
Allow safe experimentation without affecting live behavior.

### Capabilities
- Rerun backtests with modified thresholds
- Disable models temporarily
- Compare hypothetical allocations
- Preview effects before applying changes

### Why This Matters
Encourages exploration without risk.

---

## UI / UX Principles

- Model-first, not trade-first
- Clear separation between:
  - research
  - validation
  - live behavior
- Visuals over tables where possible
- Explicit uncertainty and confidence indicators

---

## Non-Goals
- Fully automated retraining from UI
- Complex financial charting
- Strategy marketing metrics

---

## Success Criteria
By the end of this sprint:
- A user with ML background can understand what each model does
- Models are easy to compare, adjust, and reason about
- The ensemble feels transparent and controllable
- The dashboard supports learning, not just monitoring

This sprint should establish **Caliper** as an ML system with *measurable judgment*, not a trading black box.
