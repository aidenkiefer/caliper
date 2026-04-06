# Dashboard UI overhaul — implementation summary

**When:** 2026-04-06 (phase 1), 2026-04-04 (phase 2 explorers)  
**Design:** [docs/superpowers/specs/2026-04-06-dashboard-ui-overhaul-design.md](../../superpowers/specs/2026-04-06-dashboard-ui-overhaul-design.md)  
**Milestone notes:** [PROGRESS.md](../PROGRESS.md) — **v2.6.0-p2** (phase 1), **v2.6.0-p3** (phase 2)

## What shipped

### Information architecture

- **`/start`** — Linear getting-started checklist with **Done / Skip / N/A** per step; progress in **`localStorage`** (`caliper-start-v1-*`).
- **`/platform`** — Searchable capability hub (table on `md+`, cards on small screens) with **track filters**; rows match `docs/api-contracts.md` status story (Live / Mock / Stub / CLI / Docs). Hub copy notes read-only explorers under **`/platform/…`**.
- **`/platform/features`** — Thin **FeatureSnapshot** explorer: `market_id`, **Load latest** / **Load history** (datetime-local window + limit), grouped collapsible families, raw JSON **Advanced** block; handles **503** (no `DB_URL`), **404**, **422**.

### Phase 2 — thin explorers (design §8 P2–P7)

- **`/platform/polymarket`** — Session list (filters, pagination) → **`/platform/polymarket/[sessionId]`** for JSON summary and lazy **Orders** / **Fills** tabs; empty list and **404** called out when API/DB stubbed.
- **`/platform/regime-allocation`** — Load global regime, allocation current, performance matrix; optional **`market_id`** for per-market regime; regime + allocation **history** with local datetime → ISO range.
- **`/platform/probability`** — Calibration + lag tests on load; optional **`model_version`** on reload; latest/history by **`market_id`**; **POST /probability/train** form.
- **`/platform/simulation`** — **POST** simulation run, immediate poll + **2s** interval until terminal status; **evaluation** compare / latest / regimes.
- **`/platform/ranking-fleet`** — **`/v1/ranking/current`**, **`/v1/fleet/status`**, signals, paper trades; **503** messaging; **Mock** badge; empty states when payloads have no rows.
- **`/platform/equities`** — Hub links to Overview, Strategies, Runs, Models, Help; **`docs/risk-policy.md`** called out in copy.

### Shared UI

- **`HelpHint`** (`apps/dashboard/src/components/help-hint.tsx`) — **`(?)`** control: **tooltip** on desktop (`md+` uses `max-width: 768px` breakpoint for “coarse” mobile sheet); **bottom sheet** on narrow viewports with **Close** + backdrop tap.
- **`StatusBadge`** — `live` | `mock` | `stub` | `cli` | `docs`.
- **`ExplorerPageHeader`** — Title + `HelpHint` + optional badges + **Back to platform**.
- **`JsonBlock`** — Scrollable `JSON.stringify` preview for stub/unknown shapes.
- **`TooltipProvider`** — Wrapped in root **`Providers`** so Radix tooltips work app-wide.
- **`DashboardFrame`** — Client shell with **dynamic header titles** for `/start`, `/platform`, all **`/platform/*`** explorers (including Polymarket session detail), and existing routes.

### Navigation

- Sidebar: **Getting started** (`BookOpen`), **Platform** (`LayoutGrid`) after Overview.

### Overview page

- **Portfolio summary** / equity / alerts section hints via `HelpHint`.
- Sprint 16 card: **`StatusBadge` Mock** beside paper badge + fleet `HelpHint`.
- Model Observatory title: `HelpHint`.
- **Baseline Comparison** card title: `HelpHint`.

### API client

- **`fetchFeatureLatest`**, **`fetchFeatureHistory`**, **`ApiHttpError`**, internal **`fetchJson`** in `apps/dashboard/src/lib/api.ts`.
- Polymarket, regime/allocation, probability, simulation/evaluation **`fetchJson`** wrappers; ranking/fleet/paper-trades also use **`fetchJson`** (consistent **`ApiHttpError`** on non-2xx).
- Types: `apps/dashboard/src/lib/types/features.ts`, **`types/explorers.ts`**; display groups: `lib/feature-display.ts`.
- Help copy map: `apps/dashboard/src/lib/help/copy.ts` (explorer `helpId`s).

## Follow-ups (optional polish)

- Charts / richer tables on history endpoints; SWR caching where helpful.
- Wire **`/platform`** rows when backend handlers move from mock/stub to live DB reads (no UI blockers).
- NextAuth ↔ FastAPI remains out of scope for this design doc.

## Files touched (high level)

- `apps/dashboard/src/app/(dashboard)/layout.tsx`, `start/page.tsx`, `platform/page.tsx`, `platform/features/page.tsx`, `platform/polymarket/page.tsx`, `platform/polymarket/[sessionId]/page.tsx`, `platform/regime-allocation/page.tsx`, `platform/probability/page.tsx`, `platform/simulation/page.tsx`, `platform/ranking-fleet/page.tsx`, `platform/equities/page.tsx`, `(dashboard)/page.tsx`
- `apps/dashboard/src/components/{dashboard-frame,explorer-page-header,help-hint,json-block,status-badge}.tsx`, `sidebar.tsx`, `providers.tsx`, `baseline-comparison.tsx`, `ui/textarea.tsx`
- `apps/dashboard/src/lib/{api.ts,platform-capabilities.ts,feature-display.ts,help/copy.ts}`, `types/features.ts`, `types/explorers.ts`
- `apps/dashboard/src/hooks/use-media-query.ts`
- Docs: this file, `PROGRESS.md`, `INDEX.md`, `FEATURES.md`, `dashboard-spec.md`, `user-guide.md`, design spec status + §8
