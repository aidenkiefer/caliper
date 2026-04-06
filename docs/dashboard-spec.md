# Dashboard Specification (Next.js)

## Summary

This document specifies the User Interface and Experience (UI/UX) for the Caliper dashboard. The dashboard is the command center for the **equities** stack: observability into strategies, runs, risk-related controls, system health, and (Sprints 7–9) the **Model Observatory** for ML lifecycle and evaluation. **Polymarket** session analytics are primarily API/SQL today (`/v1/polymarket/*`, `pm.*`); **Sprint 16** adds read-only **ranking + fleet + regime timeline** panels (`apps/dashboard/src/components/sprint-16/`) that call **`/v1/ranking/*`**, **`/v1/fleet/*`**, and regime/allocation routes — note **`/v1/ranking/*` and `/v1/fleet/*` are still mock-backed** at the API until wired (see **[docs/api-contracts.md](api-contracts.md)**). Deeper live Polymarket trading UI remains a future enhancement (see Polymarket spec §Phase 2+).

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
8.  **Help / Glossary** (`/help`)

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

### 7. Help / Glossary (`/help`)
**Goal:** Educational resource for users unfamiliar with trading terminology.

**Components:**
*   **Search Bar:** Filter glossary terms.
*   **Glossary Table:** Alphabetized list of trading terms with definitions.
*   **Category Sections:**
    *   *Performance Metrics:* P&L, Sharpe Ratio, Max Drawdown, Win Rate, Profit Factor
    *   *Risk Metrics:* Drawdown, Risk %, Stop Loss, Take Profit
    *   *Position Terms:* Long, Short, Entry, Mark Price, Unrealized P&L
    *   *Strategy Terms:* Backtest, Paper Trading, Live Trading, Signal

**Key Terms to Define:**
| Term | Definition |
|------|------------|
| **P&L** | Profit and Loss - the money made or lost on trades |
| **Sharpe Ratio** | Risk-adjusted return metric. Higher = better risk-adjusted performance. >1 is good, >2 is excellent |
| **Max Drawdown** | Largest peak-to-trough decline in portfolio value. Measures worst-case loss |
| **Win Rate** | Percentage of trades that were profitable |
| **Profit Factor** | Gross profit / gross loss. >1 means profitable overall |
| **Drawdown** | Current decline from the portfolio's peak value |
| **Long** | Buying an asset expecting price to rise |
| **Short** | Selling borrowed asset expecting price to fall |

---

## Educational Tooltips

**Goal:** Provide instant context for trading terminology without leaving the page.

**Implementation:**
*   Use Shadcn/UI `Tooltip` component with `?` icon trigger.
*   Add tooltips to:
    *   StatsCard labels (P&L, Sharpe Ratio, Max Drawdown, Win Rate)
    *   Table column headers (all pages)
    *   Chart legends
*   Tooltip content matches glossary definitions.
*   Optional: "Learn more" link to `/help` page.

**Example:**
```
┌─────────────────────────────────┐
│  Sharpe Ratio  (?)              │
│      1.85                       │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│ Risk-adjusted return metric.                │
│ Higher = better. >1 good, >2 excellent.     │
│ [Learn more →]                              │
└─────────────────────────────────────────────┘
```

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

## Implementation status

Sprints **4**, **6**, and **9** delivered the core dashboard described in this spec (layout, overview, strategies/runs/health/settings, Help/tooltips/Vercel from Sprint 6, Model Observatory from Sprint 9). **Sprint 16** added Polymarket research panels (market ranker, fleet status, regime timeline) under **`apps/dashboard/src/components/sprint-16/`**. **v2.6.0-p2** added **`/start`** (getting-started checklist), **`/platform`** (capability map + honest Live/Mock/Stub/CLI/Docs badges), **`/platform/features`** (Sprint 12 snapshot explorer), and shared **`HelpHint`** contextual help. **v2.6.0-p3** added thin read-only **platform explorers**: Polymarket sessions (list + detail), regime/allocation, probability, simulation/evaluation, ranking/fleet, and an **equities hub** — each with **`HelpHint`**, status badges where appropriate, and **`JsonBlock`** / tables for API responses (see design spec §8). Design: **[docs/superpowers/specs/2026-04-06-dashboard-ui-overhaul-design.md](superpowers/specs/2026-04-06-dashboard-ui-overhaul-design.md)**; summary: **[docs/plans/summaries/DASHBOARD-UI-OVERHAUL-2026-04.md](plans/summaries/DASHBOARD-UI-OVERHAUL-2026-04.md)**. For a feature-level list, see **[docs/FEATURES.md](FEATURES.md)**.

**May still be partial vs this checklist:** NextAuth wired end-to-end to FastAPI (verify in `apps/dashboard/`). Treat remaining items below as verify-in-code, not as open sprint backlog.

| Area | Status (verify in repo) |
|------|-------------------------|
| Next.js 14 App Router shell, Shadcn/UI, SWR hooks | Delivered (Sprint 4+) |
| Help page, glossary, tooltips | Delivered (Sprint 6) |
| `vercel.json`, API URL env | Delivered (Sprint 6) |
| Model Registry / detail / ML viz / lifecycle (Observatory) | Delivered (Sprint 9) |
| Polymarket ranker / fleet / regime panels | Delivered (Sprint 16); API data for ranking/fleet may be mock until backend wiring |
| Getting started, platform map, features explorer, HelpHint | Delivered (v2.6.0-p2) |
| Platform explorers (Polymarket, regime/allocation, probability, simulation, ranking/fleet, equities hub) | Delivered (v2.6.0-p3) |
| NextAuth ↔ FastAPI JWT | Planned / partial — confirm against implementation |
