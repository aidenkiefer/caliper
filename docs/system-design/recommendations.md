# Recommendations (HITL) — System Design

## Goal

The Recommendations surface exists to make the platform safer and more effective by presenting **machine-generated suggestions** that a human can **approve / reject** (with rationale) before they take effect.

This is intentionally **not** “auto-trading.” In Phase 1 (paper-first), Recommendations are meant to:

- gate **runtime actions** (trade intents) behind human review, risk checks, and kill-switch controls
- propose **strategy/model improvements** (parameter tuning, risk limits, feature changes) that improve performance over time

## Current state (as implemented)

Today, `/v1/recommendations` is backed by an **in-memory approval queue** (no persistence, no producer pipeline):

- storage: `services/ml/hitl/approval_queue.py`
- API: `services/api/routers/recommendations.py`
- UI: `apps/dashboard/src/app/(dashboard)/recommendations/page.tsx`

This means:

- the UI can render a queue if recommendations are inserted into memory
- there is **no durable history** and no consistent “source of truth”
- there is currently **no runtime** generating recommendations from real inference/evaluation outputs

## Designed source (per planning docs)

The original design intent (Sprints 7–9) is:

1. model inference produces **action recommendations** (BUY / SELL / HOLD)
2. the UI presents them in a **HITL queue**
3. the user approves/rejects, and the system logs decisions (and later can link to explanations)

See:
- `docs/SPRINTS-7-8-9-SUMMARY.md`
- `docs/SPRINT-9-COMPLETE.md`
- `docs/ui-data-audit.md`

## Updated proposal: two recommendation kinds

To support “make the bots better” (not just “approve trades”), we split Recommendations into two explicit kinds:

### 1) Action / trade recommendations (runtime)

**Purpose:** Suggest an action that would place/modify/cancel an order, or change a runtime execution posture.

Examples:
- BUY/SELL/HOLD (equities or Polymarket)
- “Reduce exposure” / “Tighten inventory skew” (market-making posture)
- “Pause strategy due to drawdown threshold” (safety action)

**Safety rule:** even when approved, execution must still flow through **risk controls** (kill switch / circuit breaker / sizing rules).

### 2) Strategy tuning recommendations (optimization)

**Purpose:** Suggest changes to improve strategy/model performance, typically sourced from evaluation/backtests/simulation and drift/performance telemetry.

Examples:
- adjust a signal threshold (e.g. `entry_threshold: 0.62 → 0.67`)
- change risk per trade or max positions
- change feature set (add/remove feature families)
- recommend “run a walk-forward optimization” or “retrain model vX with new window”

**Key difference:** these do **not** create orders. They produce a **proposed config change** (or a recommended experiment), which can be applied by updating a strategy config and then re-running evaluation/paper trading.

## Minimal data contract (conceptual)

We can keep the existing endpoints while extending the recommendation payload shape to support both kinds:

- `recommendation.kind`: `"action"` | `"strategy_tuning"`
- `recommendation.strategy_id`: optional (required for strategy tuning; often present for action recs)
- `recommendation.payload`: kind-specific structured JSON (order intent vs config patch)
- `recommendation.explanations`: optional links/ids for explainability artifacts

## UX implications (dashboard)

On `/recommendations`, show two sections or tabs:

- **Actions**: time-sensitive, review quickly, includes order intent + confidence + key rationale
- **Optimizations**: slower cadence, includes expected uplift + evidence + an “Apply patch” or “Open config diff” flow

This keeps the HITL surface coherent while making it useful for continuous improvement and tuning.

