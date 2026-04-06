"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { Header } from "@/components/header";
import { Sidebar } from "@/components/sidebar";

const TITLES: { prefix: string; title: string }[] = [
  { prefix: "/start", title: "Getting started" },
  { prefix: "/strategies", title: "Strategies" },
  { prefix: "/models", title: "Models" },
  { prefix: "/runs", title: "Runs" },
  { prefix: "/recommendations", title: "Recommendations" },
  { prefix: "/health", title: "Health" },
  { prefix: "/settings", title: "Settings" },
  { prefix: "/help", title: "Help" },
];

function titleForPath(pathname: string): string {
  if (pathname === "/") return "Overview";

  const exactPlatform: Record<string, string> = {
    "/platform": "Platform",
    "/platform/features": "Feature snapshots",
    "/platform/regime-allocation": "Regime & allocation",
    "/platform/probability": "Probability model",
    "/platform/simulation": "Simulation & evaluation",
    "/platform/ranking-fleet": "Ranking & fleet",
    "/platform/equities": "Equities hub",
    "/platform/polymarket": "Polymarket sessions",
  };
  if (exactPlatform[pathname]) return exactPlatform[pathname];

  if (
    pathname.startsWith("/platform/polymarket/") &&
    pathname !== "/platform/polymarket"
  ) {
    return "Polymarket session";
  }

  if (pathname.startsWith("/platform")) return "Platform";

  for (const { prefix, title } of TITLES) {
    if (pathname === prefix || pathname.startsWith(`${prefix}/`)) {
      return title;
    }
  }

  return "Dashboard";
}

export function DashboardFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const title = titleForPath(pathname ?? "/");

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div className="md:pl-64">
        <Header title={title} />
        <main className="p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
