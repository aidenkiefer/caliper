# Dashboard UI/UX overhaul — design spec

**Date:** 2026-04-06  
**Status:** Implemented through **phase 2** (thin explorers P2–P7 — 2026-04-04). Phase 1: [PROGRESS.md](../../plans/PROGRESS.md) **v2.6.0-p2**; phase 2: **v2.6.0-p3**. Summary: [DASHBOARD-UI-OVERHAUL-2026-04.md](../../plans/summaries/DASHBOARD-UI-OVERHAUL-2026-04.md).  
**Repo:** Caliper (`quant`) — `apps/dashboard` (Next.js 14, App Router, Shadcn/UI)

## 1. Goals

1. **Visibility:** Every major backend capability is **discoverable** in the UI: a page, a hub row, or an explicit **docs/CLI-only** note—never “invisible.”
2. **Clarity for a learning operator:** Dense metrics remain available, but **defaults are explainable**; jargon is optional (expand/`?`).
3. **Honest data status:** Surfaces show **Live / Mock / Stub / CLI-only** where applicable (aligned with `docs/api-contracts.md`).
4. **Guided use:** A dedicated **`/start`** checklist leads through setup and daily ops.
5. **Contextual help:** **`(?)` affordances** on sections and key metrics—**hover + focus → tooltip** on desktop; **tap → bottom sheet or popover** on touch (stays open until dismissed).
6. **Performance:** Prefer **lazy routes**, **skeletons**, **SWR/React Query** caching, and **pagination** on history endpoints; avoid loading huge JSON trees without collapse/virtualization.

## 2. Persona and principles

- **Primary:** Solo builder, **first quant/trading project**—wants **story + orientation** as much as raw density.
- **Principles:**
  - **Progressive disclosure:** short label → `?` / Advanced → full detail.
  - **One spine:** Setup → strategies/bots → health → performance → research—reflected in `/start` and cross-links.
  - **Accessibility:** `?` is a **focusable control**; tooltips work with **keyboard**; touch uses **sheet/popover**, not hover-only.

## 3. Information architecture

### 3.1 Sidebar (daily use)

Keep existing items; **add:**

| Item | Route | Purpose |
|------|-------|---------|
| **Getting started** | `/start` | Linear checklist (Done / Skip / N/A per step) |
| **Platform** | `/platform` | Capability index: status, link, one-line story |

Optional later: group labels (e.g. “Research”)—**not required for phase 1** if nav stays flat with two new links.

### 3.2 `/platform` hub

- **Desktop:** filterable **table** (search + optional category filter): Capability · Track · Status · Description · Primary link (in-app or docs).
- **Mobile:** **stacked cards**; same fields.
- **Rows** include: Equities overview, Strategies, Runs, Models, Health, Polymarket sessions (API), **Feature snapshots** (explorer), Regime/allocation, Probability, Simulation/evaluation, Ranking/fleet, Settings, Help, CLI-only bots (`polymarket-session`), etc.
- Each row shows a **status badge** (see §6).

### 3.3 `/start` checklist

- **Linear** list; each step: **Done** · **Skip** · **N/A** (no branching wizard).
- **Persistence (recommended v1):** `localStorage` keys per step; no backend.
- **Draft steps:**
  1. Environment (API URL, optional `DB_URL` note vs `DATABASE_URL`).
  2. Database migrations applied.
  3. Equities: Alpaca paper + `TRADING_MODE=PAPER` + link to risk policy.
  4. Optional Polymarket: link **POLYMARKET-QUICKSTART**, dry-run emphasis.
  5. Dashboard map: where Overview, Strategies, Models, Runs, Health, **Platform**, **Features** live; mock vs live callout.
  6. Daily loop: Health → Runs/performance → alerts.

## 4. Help system: `HelpHint` pattern

### 4.1 Component contract (conceptual)

- **Trigger:** icon button **`(?)`** next to section title or inline by metric; `aria-label="Explain {topic}"`.
- **Desktop:** Shadcn **Tooltip** (or Radix Tooltip)—open on **hover** and **focus**; Esc closes.
- **Mobile / touch:** same trigger opens **Sheet** (bottom) or **Popover** with **scroll** for long copy; **Close** + click-outside.
- **Content:** short string in code or imported from a **`help/copy.ts`** (or MD snippets) map keyed by `helpId`—keeps copy centralized for glossary sync later.
- **Optional:** “Read more” link to `docs/user-guide.md` anchors or Help page.

### 4.2 Rollout

- **Phase 1:** Implement **`HelpHint`** + apply to **`/start`**, **`/platform`**, **Overview** key cards, **Features explorer**—then expand file-by-file.

## 5. Phase 1 implementation scope (approved direction)

| Deliverable | Included |
|-------------|----------|
| **`/start`** | Page + nav link + localStorage checklist |
| **`/platform`** | Static or config-driven capability table/cards + search |
| **`HelpHint`** | Shared component; tooltip + sheet; first batch of `helpId`s |
| **Status badges** | Reusable badge on hub rows and relevant widgets (Overview, explorers) |
| **Features explorer** | First **thin** read-only page (§7) |
| **Docs** | This spec + **§8 roadmap** for more explorers |

**Out of phase 1:** Full coverage of every `?` on every widget; heavy charting; write actions not already in app.

## 6. Status badges (canonical)

| Badge | Meaning |
|-------|---------|
| **Live** | Route hits API backed by DB or real service; data may still be empty (show empty state). |
| **Mock** | API returns fixed/stub payload (e.g. `/v1/ranking/*`, `/v1/fleet/*`). |
| **Stub** | API contract exists; handler not fully wired (e.g. parts of simulation/probability). |
| **CLI** | No dashboard control; run from terminal (e.g. `polymarket-session`). |
| **Docs** | Explained only in documentation link from hub. |

Reference: **`docs/api-contracts.md`** (Sprint 15 vs 16 note and per-router notes).

## 7. Features explorer (first thin page)

**Route:** `/platform/features` **or** `/research/features` — **decision:** use **`/research/features`** if we introduce a `research` segment later; **phase 1 recommendation:** **`/platform/features`** to avoid new top-level nav section until more explorers exist.

### 7.1 API (existing)

- `GET /v1/features/{market_id}/latest` → `FeatureSnapshot` (503 if no `DB_URL`, 404 if no rows).
- `GET /v1/features/{market_id}/history?start=&end=&limit=` (cap e.g. 100–500 in UI).

### 7.2 UI

- **Input:** `market_id` text field (required); optional presets later (e.g. from Polymarket session list—**phase 2**).
- **Actions:** “Load latest”, “Load history” (with date range + limit).
- **Latest view:** Group fields by **Sprint 12 families** (market state, microstructure, probabilistic, regime) using snapshot shape—**collapsible sections** + `?` per group. Raw JSON in **“Advanced”** `<details>` or secondary tab.
- **History view:** Table of timestamps + key scalars or expandable row; charting **optional phase 2**.
- **States:** loading skeleton; 503 → explain **`DB_URL`**; 404 → “no features for this market yet”; network error → retry.
- **Badge:** **Live** when `DB_URL` set; **Unavailable** (or gray **Live** with subtext) when client gets 503—detect via health or first fetch.

### 7.3 Performance

- Debounce market_id submit; cache latest per `market_id` via SWR; history limited by `limit`; avoid rendering full JSON in main tree for large payloads.

## 8. Explorer expansion roadmap

**Thin read-only** pages (list/detail or lookup + badges + `?`) shipped for P1–P7; charts/actions remain optional follow-ups.

| Priority | Area | Route (dashboard) | API / source | Notes |
|----------|------|-------------------|--------------|--------|
| **P1** | **Feature snapshots** | `/platform/features` | `/v1/features/*` | This spec §7. **Done** (phase 1). |
| **P2** | **Polymarket sessions** | `/platform/polymarket`, `/platform/polymarket/[sessionId]` | `/v1/polymarket/sessions`, detail routes | **Done** (`v2.6.0-p3`). |
| **P3** | **Regime + allocation** | `/platform/regime-allocation` | `/v1/regime/*`, `/v1/allocation/*` | **Done** — live when `DB_URL`; global vs market scope. |
| **P4** | **Probability model** | `/platform/probability` | `/v1/probability/*` | **Done** — stub/mock badges per api-contracts. |
| **P5** | **Simulation + evaluation** | `/platform/simulation` | `/v1/simulation/*`, `/v1/evaluation/*` | **Done** — POST + poll + evaluation helpers. |
| **P6** | **Ranking + fleet** | `/platform/ranking-fleet` | `/v1/ranking/*`, `/v1/fleet/*` | **Done** — mock badge; 503 copy when `DB_URL` missing. |
| **P7** | **Equity-specific** | `/platform/equities` | Existing pages (`/`, `/strategies`, `/runs`, …) | **Done** — hub links + risk doc pointer. |

**Cross-cutting for each explorer:** `HelpHint`, status badge, link from **`/platform`**, empty/error states, mobile sheet for long help.

## 9. Visual / creative direction (phase 1)

- **Default:** stay consistent with **existing Shadcn + Caliper** theme; **no full re-skin** in phase 1.
- **Optional “creative” pass** (later ticket): one **mission-control** or **bento** variant of **Overview** only—after baseline ships.

## 10. Testing and review (human)

- Keyboard: tab to `?`, open explanation, Esc close.
- Mobile viewport: tap `?`, sheet scroll, dismiss.
- With/without `DB_URL`: Features explorer messaging correct.

## 11. Out of scope (this design)

- NextAuth ↔ FastAPI full wiring (known partial).
- Changing backend contracts.
- Live trading or real-money flows beyond documenting paper-first.

## 12. Next steps

1. **Polish (optional):** Charts, SWR caching on history endpoints, richer empty states as APIs gain real rows.  
2. **Backend wiring:** When ranking/fleet/simulation/probability handlers move beyond mocks, keep **`docs/api-contracts.md`** and hub **status badges** in sync.  
3. **Optional:** Browser **visual companion** for hub + explorer layout polish.

---

**References:** `docs/user-guide.md`, `docs/api-contracts.md`, `docs/dashboard-spec.md`, `docs/FEATURES.md`, `services/api/routers/features.py`.
