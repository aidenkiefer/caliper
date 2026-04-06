import type { CapabilityStatus } from "@/components/status-badge";

export interface PlatformCapability {
  id: string;
  name: string;
  track: string;
  status: CapabilityStatus;
  description: string;
  /** In-app path, or empty if none */
  href: string;
}

/**
 * Single source for /platform hub rows. Align with docs/api-contracts.md.
 */
export const PLATFORM_CAPABILITIES: PlatformCapability[] = [
  {
    id: "overview",
    name: "Overview",
    track: "Equities",
    status: "live",
    description: "Portfolio KPIs, equity curve, alerts, and cross-links to models and baselines.",
    href: "/",
  },
  {
    id: "strategies",
    name: "Strategies",
    track: "Equities",
    status: "live",
    description: "List and inspect strategy configs and performance hooks.",
    href: "/strategies",
  },
  {
    id: "runs",
    name: "Runs",
    track: "Equities",
    status: "live",
    description: "Backtest and execution run history.",
    href: "/runs",
  },
  {
    id: "models",
    name: "Model Observatory",
    track: "ML",
    status: "live",
    description: "Model registry, drift, lifecycle, and evaluation UI.",
    href: "/models",
  },
  {
    id: "recommendations",
    name: "Recommendations",
    track: "ML",
    status: "stub",
    description: "HITL / recommendation queue when API is wired.",
    href: "/recommendations",
  },
  {
    id: "health",
    name: "Health",
    track: "System",
    status: "live",
    description: "API and dependency health checks.",
    href: "/health",
  },
  {
    id: "settings",
    name: "Settings",
    track: "System",
    status: "live",
    description: "Dashboard preferences and environment hints.",
    href: "/settings",
  },
  {
    id: "help",
    name: "Help & glossary",
    track: "System",
    status: "docs",
    description: "In-app terminology; full guides live in repo docs/.",
    href: "/help",
  },
  {
    id: "features",
    name: "Feature snapshots",
    track: "Polymarket research",
    status: "live",
    description: "Sprint 12 FeatureSnapshot reader (pm.features via API; requires server DB_URL).",
    href: "/platform/features",
  },
  {
    id: "polymarket-api",
    name: "Polymarket sessions (API)",
    track: "Polymarket",
    status: "live",
    description: "Session list and detail (orders/fills) via GET /v1/polymarket/sessions; list may be empty until pm.sessions is wired.",
    href: "/platform/polymarket",
  },
  {
    id: "polymarket-cli",
    name: "Polymarket bot (CLI)",
    track: "Polymarket",
    status: "cli",
    description: "Live market-making: polymarket-session from services/polymarket. See docs/POLYMARKET-QUICKSTART.md.",
    href: "/start",
  },
  {
    id: "simulation",
    name: "Simulation & evaluation",
    track: "Research",
    status: "stub",
    description: "POST simulation run + poll result; evaluation compare/latest/regimes — stubs until runner/DB wired.",
    href: "/platform/simulation",
  },
  {
    id: "probability",
    name: "BTC probability model",
    track: "ML",
    status: "stub",
    description: "Calibration, lag tests, predictions — partial mock responses per Sprint 14.",
    href: "/platform/probability",
  },
  {
    id: "regime-allocation",
    name: "Regime & allocation",
    track: "Research",
    status: "live",
    description: "Sprint 15: regime and allocation JSON when API DB_URL is set.",
    href: "/platform/regime-allocation",
  },
  {
    id: "ranking-fleet",
    name: "Ranking & paper fleet",
    track: "Research",
    status: "mock",
    description: "Sprint 16: ranking/current, fleet status, signals, paper trades — often mock JSON until handlers use pm.*.",
    href: "/platform/ranking-fleet",
  },
  {
    id: "equities-hub",
    name: "Equities hub",
    track: "Equities",
    status: "live",
    description: "Shortcuts to overview, strategies, runs, models, and in-app help.",
    href: "/platform/equities",
  },
];
