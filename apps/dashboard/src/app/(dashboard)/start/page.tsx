"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Check, Circle, SkipForward, Ban } from "lucide-react";

import { HelpHint } from "@/components/help-hint";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const STORAGE_PREFIX = "caliper-start-v1";

type StepState = "pending" | "done" | "skip" | "na";

interface StepDef {
  id: string;
  title: string;
  body: string;
  links?: { href: string; label: string }[];
}

const STEPS: StepDef[] = [
  {
    id: "env",
    title: "Environment & API URL",
    body: "Confirm the dashboard can reach the FastAPI backend. In development, NEXT_PUBLIC_API_URL is usually http://localhost:8000/v1. The API container may set DATABASE_URL; several research routes also require DB_URL on the server—see docs/user-guide.md.",
    links: [{ href: "/health", label: "Check health" }],
  },
  {
    id: "db",
    title: "Database migrations",
    body: "From services/data run alembic upgrade head so equity and pm.* tables (through 007) exist.",
  },
  {
    id: "alpaca",
    title: "Equities: Alpaca paper trading",
    body: "Use paper API keys and TRADING_MODE=PAPER in configs/environments/.env. Read docs/risk-policy.md before any live path.",
    links: [{ href: "/strategies", label: "Strategies" }],
  },
  {
    id: "polymarket",
    title: "Optional: Polymarket bot",
    body: "If you use hourly BTC market-making, follow docs/POLYMARKET-QUICKSTART.md—start with polymarket-session --dry-run. Capital and safety are separate from Alpaca.",
  },
  {
    id: "dashboard-map",
    title: "Know your dashboard",
    body: "Overview shows portfolio KPIs and Sprint 16 research widgets (ranking/fleet are mock JSON until wired). Use Platform for the full capability map. Feature snapshots live under Platform → Feature snapshots.",
    links: [
      { href: "/platform", label: "Platform map" },
      { href: "/platform/features", label: "Feature snapshots" },
    ],
  },
  {
    id: "daily",
    title: "Daily loop",
    body: "Health → Runs / performance → Alerts. Use Models for ML lifecycle when you run strategies with models attached.",
    links: [
      { href: "/health", label: "Health" },
      { href: "/runs", label: "Runs" },
    ],
  },
];

function loadState(id: string): StepState {
  if (typeof window === "undefined") return "pending";
  const v = window.localStorage.getItem(`${STORAGE_PREFIX}-${id}`);
  if (v === "done" || v === "skip" || v === "na") return v;
  return "pending";
}

export default function StartPage() {
  const [states, setStates] = useState<Record<string, StepState>>({});

  useEffect(() => {
    const next: Record<string, StepState> = {};
    for (const s of STEPS) {
      next[s.id] = loadState(s.id);
    }
    setStates(next);
  }, []);

  const setStep = (id: string, state: StepState) => {
    window.localStorage.setItem(`${STORAGE_PREFIX}-${id}`, state);
    setStates((prev) => ({ ...prev, [id]: state }));
  };

  const resetAll = () => {
    for (const s of STEPS) {
      window.localStorage.removeItem(`${STORAGE_PREFIX}-${s.id}`);
    }
    const next: Record<string, StepState> = {};
    for (const s of STEPS) next[s.id] = "pending";
    setStates(next);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            Getting started
            <HelpHint helpId="start-page" label="Getting started checklist" />
          </h2>
          <p className="text-muted-foreground mt-1 text-sm">
            Linear checklist. Done / Skip / N/A per step. Progress is stored in this browser only.
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={resetAll}>
          Reset progress
        </Button>
      </div>

      <ol className="space-y-4">
        {STEPS.map((step, index) => {
          const st = states[step.id] ?? "pending";
          return (
            <li key={step.id}>
              <Card
                className={
                  st === "done"
                    ? "border-emerald-500/40"
                    : st === "na" || st === "skip"
                      ? "border-muted opacity-90"
                      : undefined
                }
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start gap-3">
                    <span
                      className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-muted text-sm font-medium"
                      aria-hidden
                    >
                      {index + 1}
                    </span>
                    <div className="min-w-0 flex-1 space-y-1">
                      <CardTitle className="text-base flex items-center gap-2">
                        {st === "done" ? (
                          <Check
                            className="h-5 w-5 text-emerald-500 shrink-0"
                            aria-label="Done"
                          />
                        ) : st === "skip" ? (
                          <SkipForward
                            className="h-5 w-5 text-muted-foreground shrink-0"
                            aria-label="Skipped"
                          />
                        ) : st === "na" ? (
                          <Ban
                            className="h-5 w-5 text-muted-foreground shrink-0"
                            aria-label="Not applicable"
                          />
                        ) : (
                          <Circle
                            className="h-5 w-5 text-muted-foreground shrink-0"
                            aria-label="Pending"
                          />
                        )}
                        {step.title}
                      </CardTitle>
                      <CardDescription className="text-sm leading-relaxed">
                        {step.body}
                      </CardDescription>
                      {step.links?.length ? (
                        <ul className="flex flex-wrap gap-2 pt-2">
                          {step.links.map((l) => (
                            <li key={l.href}>
                              <Button variant="link" className="h-auto p-0" asChild>
                                <Link href={l.href}>{l.label}</Link>
                              </Button>
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex flex-wrap gap-2 pl-11">
                    <Button
                      type="button"
                      size="sm"
                      variant={st === "done" ? "default" : "secondary"}
                      onClick={() => setStep(step.id, "done")}
                    >
                      Done
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant={st === "skip" ? "default" : "outline"}
                      onClick={() => setStep(step.id, "skip")}
                    >
                      Skip
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant={st === "na" ? "default" : "outline"}
                      onClick={() => setStep(step.id, "na")}
                    >
                      N/A
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
