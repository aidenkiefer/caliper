"use client";

import Link from "next/link";
import { ArrowRight, Activity, Brain, DollarSign, TrendingUp, Wallet } from "lucide-react";

import { AlertsWidget } from "@/components/alerts-widget";
import { BaselineComparison } from "@/components/baseline-comparison";
import { HelpHint } from "@/components/help-hint";
import { ComparisonTable, FleetOverview, RankerTable, RegimeTimeline, SignalLog } from "@/components/sprint-16";
import { EquityChart } from "@/components/equity-chart";
import { StatsCard } from "@/components/stats-card";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAlerts, useFleetSignals, useFleetStatus, useMetrics, useRankingUniverse } from "@/lib/hooks";

export default function OverviewPage() {
  const { metrics } = useMetrics();
  const { alerts } = useAlerts();
  const { rankedUniverse } = useRankingUniverse();
  const { fleetStatus } = useFleetStatus();
  const { signals } = useFleetSignals(50);

  const formatCurrency = (value: string) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(parseFloat(value));

  const formatPercent = (value: string) => {
    const num = parseFloat(value);
    const sign = num >= 0 ? "+" : "";
    return `${sign}${num.toFixed(2)}%`;
  };

  const pnlPositive = parseFloat(metrics.total_pnl_percent) >= 0;
  const drawdownNegative = parseFloat(metrics.max_drawdown) < 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold tracking-tight">Portfolio summary</h2>
        <HelpHint helpId="overview-kpis" label="Portfolio KPIs" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total P&L"
          value={formatCurrency(metrics.total_pnl)}
          change={formatPercent(metrics.total_pnl_percent)}
          changeType={pnlPositive ? "positive" : "negative"}
          icon={DollarSign}
        />
        <StatsCard
          title="Sharpe Ratio"
          value={metrics.sharpe_ratio}
          change="Annualized"
          changeType="neutral"
          icon={TrendingUp}
        />
        <StatsCard
          title="Max Drawdown"
          value={formatPercent(metrics.max_drawdown)}
          change={drawdownNegative ? "Within limits" : "At risk"}
          changeType={drawdownNegative ? "positive" : "negative"}
          icon={Activity}
        />
        <StatsCard
          title="Capital Deployed"
          value={formatCurrency(metrics.capital_deployed)}
          change={`${metrics.active_positions} positions`}
          changeType="neutral"
          icon={Wallet}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium text-muted-foreground">Equity curve</h3>
            <HelpHint helpId="overview-equity-chart" label="Equity curve" />
          </div>
          <EquityChart data={metrics.equity_curve} />
        </div>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium text-muted-foreground">Alerts</h3>
            <HelpHint helpId="overview-alerts" label="Alerts" />
          </div>
          <AlertsWidget alerts={alerts} />
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <div className="space-y-2">
            <CardTitle className="flex flex-wrap items-center gap-2">
              <Brain className="h-5 w-5" />
              Sprint 16 Fleet Control
              <HelpHint helpId="sprint16-fleet" label="Sprint 16 fleet" />
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Cross-sectional ranking, paper-trading fleet status, signal logs, and regime overlays.
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1 sm:flex-row sm:items-center">
            <StatusBadge status="mock" />
            <Badge variant="outline">Paper mode</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-6 xl:grid-cols-2">
            <RankerTable universe={rankedUniverse} />
            <FleetOverview fleetStatus={fleetStatus} />
          </div>
          <div className="grid gap-6 xl:grid-cols-2">
            <SignalLog signals={signals} />
            <RegimeTimeline points={fleetStatus.regime_timeline} />
          </div>
          <ComparisonTable rows={fleetStatus.comparison} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Model Observatory
            <HelpHint helpId="model-observatory" label="Model Observatory" />
          </CardTitle>
          <Button variant="outline" size="sm" asChild>
            <Link href="/models" className="flex items-center gap-1">
              View models
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            View and manage ML models: registry, performance, drift, health, and lifecycle controls.
          </p>
        </CardContent>
      </Card>

      <BaselineComparison
        strategyReturn={parseFloat(metrics.total_pnl_percent) / 100}
        baselineReturns={{
          hold_cash: 0.0,
          buy_and_hold: 0.12,
          random: 0.05,
        }}
        regretMetrics={{
          regret_vs_cash: parseFloat(metrics.total_pnl_percent) / 100,
          regret_vs_buy_hold: parseFloat(metrics.total_pnl_percent) / 100 - 0.12,
          regret_vs_random: parseFloat(metrics.total_pnl_percent) / 100 - 0.05,
        }}
        outperforms={{
          cash: parseFloat(metrics.total_pnl_percent) > 0,
          buy_and_hold: parseFloat(metrics.total_pnl_percent) > 12,
          random: parseFloat(metrics.total_pnl_percent) > 5,
        }}
      />
    </div>
  );
}
