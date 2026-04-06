import Link from "next/link";

import { ExplorerPageHeader } from "@/components/explorer-page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function EquitiesHubPage() {
  return (
    <div className="space-y-6">
      <ExplorerPageHeader
        title="Equities hub"
        helpId="explorer-equities"
        badges={[{ status: "live", label: "Core dashboard routes for stock paper trading" }]}
      />
      <p className="text-sm text-muted-foreground max-w-3xl">
        Cross-links for the equity / Alpaca track. Polymarket and research explorers live under{" "}
        <Link className="underline underline-offset-4" href="/platform">
          Platform
        </Link>
        .
      </p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Overview</CardTitle>
            <CardDescription>Portfolio KPIs, curve, alerts.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/">Open overview</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Strategies</CardTitle>
            <CardDescription>Configs and status.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary">
              <Link href="/strategies">Strategies</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Runs</CardTitle>
            <CardDescription>Backtest and execution history.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary">
              <Link href="/runs">Runs</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Models</CardTitle>
            <CardDescription>Model observatory (Sprint 9).</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link href="/models">Models</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Risk policy</CardTitle>
            <CardDescription>
              Canonical limits and kill-switch rules: <code className="text-xs">docs/risk-policy.md</code> in the
              repository.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link href="/help">In-app glossary</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">In-app help</CardTitle>
            <CardDescription>Glossary and terms.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="ghost">
              <Link href="/help">Help</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
