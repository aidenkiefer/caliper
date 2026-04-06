# Caliper Architecture Audit & Refactor Plan (Pre-v2.1)

## Purpose

Audit current system architecture and define required refactors to:

- Unify trading logic across Equities and Polymarket
- Enable multi-strategy, multi-market expansion
- Introduce proper portfolio and capital allocation
- Prepare for v2.1+ feature development (Polymarket Phase 2/3 + ML expansion)

---

# 1. Current System Summary

## System Shape

Two parallel systems sharing a DB:

### Equities Pipeline
```
data → features → strategy → risk → OMS → Alpaca
```

### Polymarket Pipeline
```
polymarket service → quoting loop → execution → pm.* DB
```

## Strengths

- Strong modular services (data, features, ml, execution)
- ML safety layer (drift, gating, explainability)
- Clean schema + contracts (`packages/common`)
- High-quality telemetry (especially Polymarket)
- Good documentation structure

## Core Issue

❌ System is **split, not unified**

- Polymarket bypasses:
  - Strategy layer
  - Risk layer
  - OMS
- No shared portfolio or capital allocation
- Execution paths are duplicated

---

# 2. Target Architecture (Required)

## Unified Pipeline

```
DATA → FEATURES → SIGNAL → PORTFOLIO → EXECUTION → RISK → TELEMETRY
```

## Design Goals

- One signal interface for all strategies
- One portfolio allocator for all capital
- One execution abstraction with market adapters
- One risk system across all markets

---

# 3. Key Gaps (Must Fix)

## 3.1 No Portfolio Layer (CRITICAL)

### Current
- Signals go directly to execution

### Problem
- No capital allocation logic
- No cross-strategy coordination
- No exposure management

### Required

Create:
```
services/portfolio/allocator.py
```

Responsibilities:
- Convert signals → position targets
- Allocate capital across:
  - strategies
  - markets
- Enforce:
  - max exposure
  - position sizing
  - diversification rules

---

## 3.2 Strategy Interface Too Narrow

### Current
```
generate_signals()
```

### Problem
- Only supports equities-style signals
- Cannot represent:
  - probabilistic markets
  - market making
  - hybrid strategies

### Required

Refactor to:

```
generate_signal(context) → Signal
```

Signal schema:

```
Signal:
  asset_id
  market_type
  signal_type        # directional | market_making | hybrid
  direction          # long / short / none
  confidence         # 0–1
  horizon            # time-based
  metadata           # strategy-specific
```

---

## 3.3 Execution System Fragmented

### Current
- `services/execution` → Alpaca
- `services/polymarket` → separate executor

### Problem
- Duplicate logic
- No shared interface
- Hard to scale to new markets

### Required

Create unified interface:

```
ExecutionAdapter:
  place_order()
  cancel_order()
  get_positions()
  get_orderbook()
```

Implementations:
- `AlpacaAdapter`
- `PolymarketAdapter`

---

## 3.4 Risk Layer Not Unified

### Current
- Equities → full RiskManager
- Polymarket → custom “safety layer”

### Problem
- Inconsistent risk controls
- Capital not managed globally

### Required

```
GlobalRiskManager
  + MarketSpecificRiskExtensions
```

Global:
- drawdown limits
- capital usage
- kill switch

Market-specific:
- Polymarket inventory caps
- Equities position constraints

---

## 3.5 Polymarket Logic in Wrong Layer

### Current
- Quoting + strategy logic inside `services/polymarket`

### Problem
- Not reusable
- Not composable with other strategies
- Cannot integrate ML or directional overlays

### Required

Split into:

```
services/polymarket/
  adapters (CLOB, Gamma, Binance)
  execution

packages/strategies/
  polymarket_mm_strategy.py
  polymarket_directional_strategy.py
```

---

## 3.6 No Market Abstraction

### Current
- Market logic implicit in services

### Required

```
MarketType:
  EQUITY
  PREDICTION
  CRYPTO (future)
```

Each defines:
- execution rules
- pricing model
- constraints

---

# 4. Required Refactor Plan (Ordered)

## Step 1 — Add Portfolio Layer

Create:
```
services/portfolio/
  allocator.py
```

Implement:
- position sizing
- capital allocation
- exposure limits

---

## Step 2 — Refactor Strategy Interface

Update:
```
packages/strategies/base.py
```

Support:
- directional signals
- probabilistic signals
- MM configs

---

## Step 3 — Create Execution Adapter Interface

Refactor:
```
services/execution/
```

Move:
- shared logic → base adapter
- Alpaca → adapter
- Polymarket → adapter

---

## Step 4 — Extract Polymarket Strategy Logic

Move:
- quoting logic → strategy layer

Keep in service:
- API clients
- execution plumbing

---

## Step 5 — Unify Risk Layer

Create:
```
services/risk/global_risk_manager.py
```

Integrate:
- Polymarket into global risk checks

---

## Step 6 — Standardize Telemetry

Ensure all strategies emit:
- PnL
- exposure
- signal quality
- execution metrics

---

# 5. What NOT to Change

Keep intact:

- ML safety system (drift, gating, explainability)
- Data contracts (`packages/common`)
- TimescaleDB schema structure
- Polymarket telemetry depth
- Docs structure (`docs/INDEX.md`)

---

# 6. Acceptance Criteria (Refactor Complete When)

- [ ] All strategies (equities + polymarket) use same interface
- [ ] Portfolio allocator sits between signal and execution
- [ ] Execution uses adapter pattern (no duplicated logic)
- [ ] Risk is enforced globally across all trades
- [ ] Polymarket strategies exist in `packages/strategies`
- [ ] New strategy can be added without modifying services

---

# 7. Cursor Task

Audit current codebase and:

1. Identify all violations of target architecture
2. List files that:
   - bypass strategy layer
   - bypass risk layer
   - duplicate execution logic
3. Propose:
   - exact file changes
   - new interfaces
   - migration plan (non-breaking if possible)
4. Output:
   - concrete PR plan (step-by-step)
   - no high-level suggestions, only actionable changes