# Design Guidelines — Caliper Dashboard

**Purpose:**  
Define a clear, intentional, and consistent visual system for the quantitative trading dashboard. This document ensures all design and UI decisions support clarity, rapid comprehension, and operational reliability.

This dashboard is **data-first**, **operations-focused**, and **designed for dark environments**.

---

## 1. Design Philosophy

This dashboard is:
- A command center for trading operations
- A real-time monitoring interface
- A risk management tool

Its job is to:
1. Display financial data with maximum clarity
2. Enable rapid status assessment at a glance
3. Surface critical alerts immediately
4. Minimize cognitive load during high-stress situations

Every design decision should answer:
> "Does this help the user understand portfolio status and act quickly?"

If a choice looks stylish but does not improve comprehension or speed, it should be avoided.

---

## 2. Visual Tone & Inspiration

High-level inspiration:
- Professional trading terminals (Bloomberg, TradingView)
- Operations dashboards (Grafana, Datadog)
- Cockpit instrumentation (status-at-a-glance)

Keywords:
- Professional
- Information-dense
- High-contrast
- Responsive
- Trustworthy

Avoid:
- Decorative elements
- Playful aesthetics
- Excessive animations
- Low-contrast designs
- Cluttered layouts

---

## 3. Color System

### 3.1 Dark Mode Foundation

Dark mode is the primary and only mode. Trading environments benefit from:
- Reduced eye strain during extended sessions
- Better visibility of colored indicators
- Professional appearance

**Core Colors (HSL format):**

| Token | HSL Value | Use |
|-------|-----------|-----|
| `--background` | `0 0% 3.9%` | Page background (near black) |
| `--foreground` | `0 0% 98%` | Primary text |
| `--card` | `240 6% 10%` | Card backgrounds |
| `--muted` | `240 3.7% 15.9%` | Subtle backgrounds |
| `--muted-foreground` | `240 5% 64.9%` | Secondary text |
| `--border` | `240 3.7% 15.9%` | Borders and dividers |

---

### 3.2 Semantic Trading Colors

These colors have specific meaning in financial contexts. Use consistently.

| Token | HSL Value | Hex Approx | Use |
|-------|-----------|------------|-----|
| `--profit` | `142 76% 36%` | `#22c55e` | Positive P&L, gains, healthy status |
| `--loss` | `0 84% 60%` | `#ef4444` | Negative P&L, losses, errors, danger |
| `--warning` | `45 93% 47%` | `#eab308` | Warnings, caution, degraded status |
| `--info` | `220 70% 50%` | `#3b82f6` | Informational, neutral highlights |

**Rules:**
- Green (`profit`) = money gained, system healthy, go signal
- Red (`loss`) = money lost, system error, stop signal
- Yellow (`warning`) = attention needed, degraded, caution
- Never invert these meanings

---

### 3.3 Chart Colors

For multi-series charts and visualizations:

| Token | Use |
|-------|-----|
| `--chart-1` | Primary data series (equity curve) |
| `--chart-2` | Secondary series / comparison |
| `--chart-3` | Tertiary data |
| `--chart-4` | Additional series |
| `--chart-5` | Additional series |

---

### 3.4 Interactive States

| Token | Use |
|-------|-----|
| `--card-hover` | Card hover state |
| `--row-hover` | Table row hover state |
| `--ring` | Focus ring for accessibility |

---

## 4. Typography

### 4.1 Font Stack

| Type | Font | Use |
|------|------|-----|
| **Sans-serif** | Inter | UI text, labels, headings |
| **Monospace** | Geist Mono | Financial data, numbers, code |

**Rationale:**
- Inter: Excellent legibility at small sizes, professional appearance
- Geist Mono: Clear tabular figures, designed for data display

---

### 4.2 Financial Data Typography

**Critical Rule:** All financial numbers must use:
- Monospace font (`font-mono`)
- Tabular figures (`font-variant-numeric: tabular-nums`)

This ensures:
- Decimal points align vertically
- Numbers are easy to compare
- Data tables are scannable

**CSS utility class:** `.font-tabular`

---

### 4.3 Type Scale

| Class | Size | Use |
|-------|------|-----|
| `text-xs` | 0.75rem | Timestamps, tertiary labels |
| `text-sm` | 0.875rem | Secondary text, table cells |
| `text-base` | 1rem | Body text |
| `text-lg` | 1.125rem | Card titles |
| `text-xl` | 1.25rem | Page headers |
| `text-2xl` | 1.5rem | Major KPIs, stat values |

---

## 5. Layout & Spacing

### 5.1 Dashboard Structure

```
┌─────────────────────────────────────────────────────────┐
│ Header (fixed) - Title, Alerts, Kill Switch            │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│ Sidebar  │  Main Content Area                           │
│ (fixed)  │  - Stats cards (grid)                        │
│          │  - Charts                                    │
│ 256px    │  - Tables                                    │
│          │  - Widgets                                   │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

---

### 5.2 Grid System

**Stats Cards:**
- Mobile: 1 column
- Tablet (md): 2 columns  
- Desktop (lg): 4 columns

**Main Content:**
- Use `lg:grid-cols-3` for chart + sidebar widget layout
- Primary content spans 2 columns, secondary 1 column

---

### 5.3 Spacing Scale

Use consistent spacing from Tailwind's scale:
- `gap-4` (16px): Between cards in a grid
- `gap-6` (24px): Between sections
- `p-4` / `p-6`: Card/component padding

---

### 5.4 Border Radius

| Token | Value | Use |
|-------|-------|-----|
| `rounded-sm` | 4px | Small elements |
| `rounded-md` | 6px | Buttons, inputs |
| `rounded-lg` | 8px | Cards (default) |
| `rounded-xl` | 12px | Large cards |

---

## 6. Components

### 6.1 Stats Cards

Stats cards display key metrics prominently.

**Structure:**
- Title (muted, small)
- Value (large, bold, monospace for numbers)
- Change indicator (colored by direction)
- Optional icon

**States:**
- Default: Standard card background
- Hover: Subtle background shift
- Live: Pulsing indicator for real-time data

---

### 6.2 Tables

Tables display detailed data (positions, strategies, runs).

**Guidelines:**
- Header row: muted text, sticky if scrollable
- Data rows: hover state for active row
- Numbers: right-aligned, monospace
- Status badges: colored appropriately
- Actions: right-aligned button group

---

### 6.3 Charts

**Equity Curves:**
- Use line charts with smooth interpolation
- Show grid lines (subtle)
- Tooltip on hover with formatted values
- Period selector (1D, 1W, 1M, ALL)

**Colors:**
- Positive trend: profit green
- Negative trend: loss red
- Neutral/benchmark: muted or blue

---

### 6.4 Alerts Widget

**Severity Levels:**
| Severity | Color | Icon |
|----------|-------|------|
| INFO | Blue | Info circle |
| WARNING | Yellow | Triangle |
| ERROR | Red | Circle exclamation |
| CRITICAL | Red (intense) | Circle exclamation |

---

### 6.5 Kill Switch

The emergency stop button requires special treatment:
- Prominent placement (header, always visible)
- Red/destructive styling
- Confirmation dialog before activation
- Clear indication of consequences

---

## 7. Loading & Error States

### 7.1 Loading States

Every page and widget must have a loading state.

**Pattern:**
- Use skeleton loaders that match content shape
- Maintain layout structure during loading
- Avoid spinners for content areas (use for actions)

---

### 7.2 Error States

**Pattern:**
- Clear error message
- Technical details (collapsible/muted)
- Recovery actions (retry, go home)
- Don't leave users stranded

---

## 8. Accessibility

### 8.1 Color Contrast

- All text must meet WCAG AA contrast requirements
- Never use color as the only indicator of meaning
- Pair colors with icons or text labels

---

### 8.2 Focus States

- All interactive elements must have visible focus states
- Use `ring-2 ring-ring ring-offset-2` for consistent focus styling
- Focus states must be visible in dark mode

---

### 8.3 Screen Readers

- Use semantic HTML elements
- Provide `aria-label` for icon-only buttons
- Use `role="status"` for live-updating content

---

## 9. Responsive Design

### 9.1 Breakpoints

| Prefix | Min Width | Target |
|--------|-----------|--------|
| (none) | 0px | Mobile first |
| `sm:` | 640px | Large phone |
| `md:` | 768px | Tablet |
| `lg:` | 1024px | Laptop |
| `xl:` | 1280px | Desktop |

---

### 9.2 Mobile Considerations

Trading dashboards must be mobile-accessible for:
- Quick status checks
- Emergency actions (kill switch)
- Alert acknowledgment

**Mobile-specific:**
- Collapsible sidebar (hamburger menu)
- Simplified stats display
- Large touch targets for critical actions

---

## 10. Motion & Animation

### 10.1 Allowed Motion

| Element | Animation |
|---------|-----------|
| Card hover | Background color transition (200ms) |
| Button hover | Background/scale transition (150ms) |
| Modal open | Fade + scale in (200ms) |
| Live indicator | Subtle pulse (2s loop) |

---

### 10.2 Prohibited Motion

- Page load animations
- Scroll-triggered effects
- Parallax
- Auto-playing decorative animations
- Chart animations on data update (use instant updates)

---

## 11. Risk Mitigation UX

Per the dashboard specification, implement these safety patterns:

| Risk | UX Mitigation |
|------|---------------|
| Stale data | Show "Last Updated: Xs ago" with warning if >30s |
| Fat finger | Confirmation dialog for destructive actions |
| Auth failure | Session timeout warnings, auto-redirect |
| API lag | Visual indicator when data is stale |

---

## 12. Performance Guidelines

### 12.1 Data Updates

- Polling interval: 5 seconds (configurable)
- Use React Query/SWR for caching and deduplication
- Show loading states only on initial load, not refetch

---

### 12.2 Bundle Size

- Use dynamic imports for chart libraries
- Lazy load non-critical pages
- Keep initial bundle minimal for fast first paint

---

## 13. What Not To Add

To maintain professional credibility:
- No gradients (except subtle chart fills)
- No decorative illustrations
- No playful icons or emoji
- No trend-driven effects
- No light mode (dark mode only)
- No excessive branding

The dashboard should feel like a professional tool, not a consumer app.

---

## 14. Success Criteria

The design has succeeded if:
- Portfolio status is comprehensible within 2 seconds
- Critical alerts are impossible to miss
- Emergency actions are fast and unambiguous
- The interface works reliably under stress
- A professional trader thinks: "This is a serious tool."

---

## 15. Design Token Reference

All design tokens are defined in:
- `globals.css` - CSS custom properties
- `tailwind.config.ts` - Tailwind theme extension

Use these tokens consistently. Never use arbitrary color values.
