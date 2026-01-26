# Dashboard Specification (Next.js)

## Summary

This document specifies the User Interface and Experience (UI/UX) for the monitoring dashboard. The dashboard is the command center for the trading platform, providing observability into active strategies, risk metrics, and system health, as well as control commands (kill switches, config updates).

**Tech Stack:**
- **Framework:** Next.js 14 (App Router)
- **Deployment:** Vercel
- **UI Library:** Tailwind CSS + Shadcn/UI (for premium feel)
- **Charts:** TradingView Lightweight Charts (performance) + Recharts (metrics)
- **Data Fetching:** React Query (polling) or SWR
- **Auth:** NextAuth.js

---

## Key Decisions

### ✅ Polling vs. WebSocket
**Decision:** Polling (Interval: 5s) for V1.
**Rationale:**
- Simpler implementation with Next.js Server Components.
- 5s latency is acceptable for "Risk Level 6" swing trading (not HFT).
- Reduces need for a dedicated WebSocket server maintenance in V1.

### ✅ Authentication
**Decision:** NextAuth.js (Credentials Provider)
**Rationale:**
- Simple integration with the Python FastAPI backend (exchange JWTs).
- Secure session management.
- Easy to add OAuth providers (Google/GitHub) later if needed.

### ✅ Mobile Responsiveness
**Decision:** "Mobile-First" Design.
**Rationale:**
- User should be able to check status and hit "Kill Switch" from phone immediately.

---

## Site Map / Navigation

1.  **Login** (`/auth/signin`)
2.  **Dashboard / Overview** (`/`)
3.  **Strategies** (`/strategies`)
    *   Strategy Detail (`/strategies/[id]`)
4.  **Positions** (`/positions`)
5.  **Backtests / Runs** (`/runs`)
    *   Run Report (`/runs/[id]`)
6.  **System Health** (`/health`)
7.  **Settings / Admin** (`/settings`)

---

## Page Specifications

### 1. Overview Page (`/`)
**Goal:** High-level "Pulse Check". Am I making money? Am I safe?

**Components:**
*   **Header Stats Row:**
    *   *Total Equity:* $12,450 (+1.2% Today) [Green/Red indicator]
    *   *Active Risk:* 12% Capital Deployed
    *   *Open P&L:* +$450
    *   *Day P&L:* +$120
*   **Main Chart (Equity Curve):**
    *   Line chart showing portfolio value over time (1D, 1W, 1M, ALL).
    *   Comparison line vs SPY (Benchmark).
*   **Active Alerts Widget:**
    *   List of recent warnings/errors (e.g., "Strategy A Hit Stop Loss").
*   **Global Controls:**
    *   🔴 **GLOBAL KILL SWITCH** (Big Red Button): Stops all trading, cancels orders.

### 2. Strategies Page (`/strategies`)
**Goal:** Manage the fleet of bots.

**Table Columns:**
*   **Status:** (🟢 Live / 🟡 Paper / 🔴 Stopped)
*   **Name:** "Momentum Alpha v1", "MeanRev S&P"
*   **Allocation:** $5,000 (20%)
*   **Perf (30d):** +4.5%
*   **Drawdown:** -1.2% (Max -5%)
*   **Actions:** [Pause] [Config] [View]

### 3. Strategy Detail (`/strategies/[id]`)
**Goal:** Deep dive into one strategy.

**Components:**
*   **Performance Chart:** Strategy-specific equity curve.
*   **Positions Table:** Current open positions for *this* strategy.
*   **Logs / Activity Stream:** specific log lines (e.g., "Signal Generated: BUY AAPL @ 150").
*   **Configuration Editor (YAML/JSON):**
    *   Edit parameters (e.g., `rsi_threshold: 30` -> `25`).
    *   *Action:* "Update Config" (Requires restart of strategy instance).

### 4. Positions Page (`/positions`)
**Goal:** What do I own right now?

**Table Columns:**
*   **Symbol:** AAPL, SPY, NVDA
*   **Side:** LONG / SHORT
*   **Qty:** 50
*   **Entry:** $145.00
*   **Mark:** $150.00
*   **Unrealized P&L:** +$250 (+3.4%)
*   **Risk:** Stop Loss @ $140, Take Profit @ $160
*   **Strategy:** "Momentum Alpha"

### 5. Runs / Backtests Page (`/runs`)
**Goal:** View history of experiments.

**Components:**
*   **Run History Table:**
    *   ID, Type (Backtest/Paper), Date, Strategy, Result (+10%), Artifacts (Link to Report).
*   **Trigger New Backtest:**
    *   Form: Select Strategy, Date Range, Capital.
    *   Button: "Run Backtest" (Calls API).

### 6. System Health (`/health`)
**Goal:** Debugging and Infra status.

**Components:**
*   **Service Status Grid:**
    *   Data Feed (Alpaca): 🟢 Connected (Latency: 45ms)
    *   Broker API: 🟢 Connected
    *   Database: 🟢 Healthy
    *   Redis: 🟢 Healthy
*   **API Usage:** Progress bars for rate limits (e.g., "Alpaca API: 450/1000 requests").

---

## Component Interface (Design System)

**Color Palette (Dark Mode Default):**
*   **Background:** `#09090b` (Zinc 950)
*   **Card BG:** `#18181b` (Zinc 900)
*   **Text Primary:** `#fafafa`
*   **Text Secondary:** `#a1a1aa`
*   **Profit (Green):** `#22c55e` (Emerald 500)
*   **Loss (Red):** `#ef4444` (Red 500)
*   **Alert (Yellow):** `#eab308` (Yellow 500)

**Typography:**
*   **Font:** Inter (Sans-serif) or Geist Mono (for data/tables).

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
| :--- | :--- | :--- |
| **API Lag** | Dashboard shows stale prices. | UI Indicator "Last Updated: 5s ago". Red warning if > 30s. |
| **Auth Failure** | Unauthorized access to controls. | Short session timeouts (1h). 2FA for Admin actions. |
| **Fat Finger** | Accidental "Kill Switch" press. | "Confirm" modal for destructive actions. |

---

## Open Questions

1.  **Chart Library:** Recharts is easier for Next.js, but TradingView Lightweight Charts handles financial (OHLC) data better.
    *   *Decision:* Mixed. Use TradingView for Stock/Equity curves. Use Recharts for simple bar charts (Monthly P&L).
2.  **Notifications:** Should the dashboard push browser notifications?
    *   *Decision:* Yes, useful for alerting user when app is in background tab.

---

## Implementation Tasks

*   [ ] Initialize Next.js 14 project (`npx create-next-app`).
*   [ ] Install ShadCN/UI components (Card, Table, Button, Dialog).
*   [ ] Setup NextAuth with Custom Credentials provider connecting to FastAPI.
*   [ ] Create API Client (Axios/Fetch) hook wrapper for querying Python backend.
*   [ ] Build "Global Layout" shell with Sidebar navigation.
*   [ ] Implement "Overview" page widgets.
