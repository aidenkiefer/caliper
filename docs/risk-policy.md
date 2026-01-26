# Risk Management Policy

## Summary

This document defines the comprehensive **Risk Management Policy** for the quantitative ML trading platform. Trading involves real financial risk, and this policy establishes the automated guardrails, limits, and kill switches that must be strictly enforced by the software.

**Risk Level Target:** 6–7 (Moderate)
- **Goal:** Consistent risk-adjusted returns with controlled drawdowns.
- **Philosophy:** "Live to trade another day." Capital preservation is the primary objective; profit is secondary.

**Enforcement:**
- **Pre-Trade:** Checks performed *before* any order is submitted.
- **Post-Trade:** Monitoring of open positions and portfolio health.
- **Fail-Safe:** Default to *rejecting* orders if risk checks fail or data is stale.

---

## Key Decisions

### ✅ Hard Coded Limits vs. Configurable
**Decision:** Absolute hard limits are defined in code (safety ceiling), while operational limits are configurable per strategy.
**Rationale:**
- Prevents configuration errors (e.g., accidental 100% position size).
- Allows flexibility for different strategy types (e.g., conservative vs. aggressive) within safe bounds.

### ✅ Automated Kill Switches
**Decision:** System (global) and Strategy-level kill switches trigger automatically on drawdown thresholds.
**Rationale:**
- Emotional trading leads to ruin.
- Automation removes hesitation during adverse market events.
- "Circuit breaker" logic protects against model drift or regime shifts.

### ✅ Options-Specific Guardrails
**Decision:** Restrict allowable option strategies to defined-risk types (e.g., spreads) for v1.
**Rationale:**
- Naked option selling has undefined (infinite) risk.
- Spreads cap max loss at entry.

---

## 1. Portfolio-Level Limits (System Wide)

These limits apply to the entire trading account/portfolio.

| Metric | Limit (Default) | Action on Breach |
| :--- | :--- | :--- |
| **Max Drawdown (Daily)** | 3.0% of Opening Equity | **Halt Trading** (Close all positions? Configurable, default: Halt new entries) |
| **Max Drawdown (Total)** | 10.0% from High Water Mark | **Kill Switch** (Halt all trading, alert human, require manual reset) |
| **Max Capital Deployed** | 80% of Total Liquidity | Reject new opening orders |
| **Max Open Positions** | 20 (across all strategies) | Reject new opening orders |
| **Margin Usage** | Max 1.5x (if enabled) | Reject new margin-increasing orders |

### 1.1 Kill Switch Protocol (System)
**Trigger:** Total Drawdown > 10%
**Process:**
1.  **Immediate:** Cancel all pending orders.
2.  **Immediate:** Halt all strategy execution (no new signals processed).
3.  **Action:** Close all liquid positions (or user-configurable: "Flatten" vs. "Freeze"). *Default: Freeze (manual intervention to close).*
4.  **Alert:** Send CRITICAL alert via all channels (SMS, Email, Slack).
5.  **Reset:** Requires manual admin override via API/Dashboard.

---

## 2. Strategy-Level Limits

Limits applied to individual strategy instances.

| Metric | Limit (Range) | Description |
| :--- | :--- | :--- |
| **Max Allocation** | 0–100% of Portfolio | Hard cap on how much capital one strategy can control. |
| **Max Drawdown** | 5–10% of Strategy Allocation | Pauses the specific strategy. |
| **Daily Loss Limit** | 1–2% of Strategy Allocation | Pauses strategy for remainder of trading session. |
| **Min Liquidity** | $500k Daily Volume | Strategy forbidden from trading illiquid assets. |

---

## 3. Order-Level Limits (Pre-Trade Checks)

Every order must pass these checks before submission to the Execution Engine.

### 3.1 Position Sizing
*   **Formula:** `Risk Amount / (Entry Price - Stop Loss Price)` or Fixed Fraction.
*   **Max Risk Per Trade:** 2.0% of Portfolio Equity (Absolute Hard Limit).
*   **Max Notional Per Trade:** 10.0% of Portfolio Equity (to prevent concentration).

### 3.2 Asset Restrictions
*   **Prohibited Assets:** Hardcoded blocklist (e.g., defined penny stocks, specific tickers).
*   **Min Price:** No trading stocks < $5.00 (Penny stock filter).
*   **Min Volume:** 20-day Average Volume > 500,000 shares.

### 3.3 Sanity Checks (Fat Finger Protection)
*   **Price Deviation:** Reject limit orders > 5% away from last traded price.
*   **Max Quantity:** Reject orders > 10% of average daily volume for that asset.
*   **Notional Cap:** Reject any single order > $25,000 (configurable).

---

## 4. Options Risk Policy

Options introduce leverage and complexity. V1 restricts activity to **Defined Risk** strategies.

### 4.1 Permitted Strategies
1.  **Long Calls / Puts:** Buying premium. Max loss = Premium paid.
2.  **Vertical Spreads (Debit):** Bull Call / Bear Put. Max loss = Premium paid.
3.  **Vertical Spreads (Credit):** Bear Call / Bull Put. **MUST** be fully collateralized or have strict stop loss. (Higher Risk).
4.  **Covered Calls:** Permitted only if underlying is held.

### 4.2 Prohibited Strategies (V1)
*   ❌ **Naked Call Selling:** Infinite risk. Strictly forbidden.
*   ❌ **Naked Put Selling:** High risk of assignment. Forbidden in V1.
*   ❌ **Undefined Risk Structures:** Ratio spreads / Straddles (unless long).

### 4.3 Greeks Exposure Limits
*   **Delta:** Portfolio net beta-weighted delta must stay within +/- 50% of SPY equivalent (configurable).
*   **Gamma:** Monitor proximity to expiration. "Gamma Risk" warning 3 days to expiration.
*   **Theta:** Net positive theta preferred.

### 4.4 Expiration Safety
*   **No "0DTE" (Zero Days to Expiration):** Trading blocked on expiration day.
*   **Auto-Close:** Force close options positions at 3:00 PM ET on expiration day to avoid after-hours assignment risk.

---

## 5. Technical & Operational Safeguards

### 5.1 Data Integrity
*   **Stale Data:** If market data is > 10 seconds old (live) or connection lost:
    *   **Action:** Halt new orders.
    *   **Action:** "Safe Mode" activated.
*   **Bad Data:** If `High < Low` or `Price = 0` or `Volume < 0`:
    *   **Action:** Discard data point, log error, do not trigger signals.

### 5.2 Execution Safety
*   **Idempotency:** Unique `client_order_id` required for every order to prevent duplicate submissions on retry.
*   **Rate Limiting:** Throttle order submissions to stay within Broker API limits (avoid IP ban).
*   **Reconciliation:** Every 1 minute, compare `Local State` (Database) vs. `Broker State` (API).
    *   **Mismatch?** Alert immediately. Pause trading until resolved.

---

## 6. Paper Trading vs. Live Trading

| Feature | Paper Mode | Live Mode |
| :--- | :--- | :--- |
| **Capital** | Virtual ($100k) | Real Money |
| **Broker Connection** | Paper API Endpoint | Live API Endpoint |
| **Risk Limits** | Warning Only (Log) | **Strict Enforcement (Reject)** |
| **Approvals** | None | **Human Approval** required to activate |

### Transition Gate (Paper → Live)
To promote a strategy to Live:
1.  **Backtest:** Profitable over 6 months data, Sharpe > 1.0.
2.  **Paper:** Run checking for 1 week without technical errors.
3.  **Review:** Human confirmation of logic and risk parameters.
4.  **Capital:** Allocation set < 20% of account initially.

---

## Open Questions

1.  **Flattening Logic:** When a system kill switch hits, should we *market sell* everything or just stop *new* trades? Market selling can crash price in illiquid markets.
    *   *Proposed:* Default to stopping new trades ("Freeze"). Allow manual flatten via "Panic Button" in dashboard.
2.  **Credit Spreads:** How to accurately calculate max risk for complex multi-leg credit spreads via API?
    *   *Proposed:* Use broker margin requirement calculation or simplify to width of strikes.
3.  **Overnight vs Intraday:** Do we allow holding over earnings reports?
    *   *Proposed:* Flag earnings dates. Close positions before earnings by default.

---

## Implementation Checklist

*   [ ] Implement `RiskManager` class in `services/risk`.
*   [ ] Implement pre-trade validation decorators.
*   [ ] Build "Kill Switch" toggle in Dashboard UI.
*   [ ] Configure alerting pipeline (Slack/SMS) for breaches.
*   [ ] Write unit tests for limit logic (ensure 2% risk actually blocks 3% risk).
