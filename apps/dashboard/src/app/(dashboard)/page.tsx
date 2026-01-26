"use client";

import { useMetrics, useAlerts } from "@/lib/hooks";
import { StatsCard } from "@/components/stats-card";
import { EquityChart } from "@/components/equity-chart";
import { AlertsWidget } from "@/components/alerts-widget";
import { DollarSign, TrendingUp, Activity, Wallet } from "lucide-react";

export default function OverviewPage() {
  const { metrics } = useMetrics();
  const { alerts } = useAlerts();

  const formatCurrency = (value: string) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(parseFloat(value));
  };

  const formatPercent = (value: string) => {
    const num = parseFloat(value);
    const sign = num >= 0 ? "+" : "";
    return `${sign}${num.toFixed(2)}%`;
  };

  const pnlPositive = parseFloat(metrics.total_pnl_percent) >= 0;
  const drawdownNegative = parseFloat(metrics.max_drawdown) < 0;

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
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

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <EquityChart data={metrics.equity_curve} />
        </div>
        <div>
          <AlertsWidget alerts={alerts} />
        </div>
      </div>

      {/* Additional Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <StatsCard
          title="Win Rate"
          value={`${(parseFloat(metrics.win_rate) * 100).toFixed(0)}%`}
          change={`${metrics.total_trades} total trades`}
          changeType="neutral"
        />
        <StatsCard
          title="Active Positions"
          value={metrics.active_positions.toString()}
          change="Across all strategies"
          changeType="neutral"
        />
        <StatsCard
          title="Available Capital"
          value={formatCurrency(metrics.available_capital)}
          change="Ready to deploy"
          changeType="neutral"
        />
      </div>
    </div>
  );
}
