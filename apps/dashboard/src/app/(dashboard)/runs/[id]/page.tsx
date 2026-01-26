"use client";

import { useRun } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatsCard } from "@/components/stats-card";
import { EquityChart } from "@/components/equity-chart";
import { ArrowLeft, Download, CheckCircle, Loader2, XCircle } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { use } from "react";

interface RunDetailPageProps {
  params: Promise<{ id: string }>;
}

const statusConfig = {
  RUNNING: { label: "Running", icon: Loader2, color: "bg-warning text-white" },
  COMPLETED: { label: "Completed", icon: CheckCircle, color: "bg-profit text-white" },
  FAILED: { label: "Failed", icon: XCircle, color: "bg-loss text-white" },
};

export default function RunDetailPage({ params }: RunDetailPageProps) {
  const { id } = use(params);
  const { run } = useRun(id);

  if (!run) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Run not found</p>
      </div>
    );
  }

  const formatCurrency = (value: string) => {
    const num = parseFloat(value);
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(num);
  };

  const formatPercent = (value: string) => {
    const num = parseFloat(value);
    const sign = num >= 0 ? "+" : "";
    return `${sign}${num.toFixed(2)}%`;
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatDateTime = (date: string) => {
    return new Date(date).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const status = statusConfig[run.status];
  const StatusIcon = status.icon;
  const returnPositive = parseFloat(run.total_return) >= 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Link href="/runs">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-2xl font-bold">Backtest Report</h2>
              <Badge className={cn(status.color)}>
                <StatusIcon
                  className={cn(
                    "h-3 w-3 mr-1",
                    run.status === "RUNNING" && "animate-spin"
                  )}
                />
                {status.label}
              </Badge>
              <Badge variant="outline">{run.run_type}</Badge>
            </div>
            <p className="text-muted-foreground">
              {run.strategy_id} • {formatDate(run.start_date)} -{" "}
              {formatDate(run.end_date)}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="gap-2">
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Return"
          value={formatPercent(run.metrics.total_return)}
          change={`CAGR: ${formatPercent(run.metrics.cagr)}`}
          changeType={returnPositive ? "positive" : "negative"}
        />
        <StatsCard
          title="Sharpe Ratio"
          value={run.metrics.sharpe_ratio}
          change={`Sortino: ${run.metrics.sortino_ratio}`}
          changeType={parseFloat(run.metrics.sharpe_ratio) >= 1.5 ? "positive" : "neutral"}
        />
        <StatsCard
          title="Max Drawdown"
          value={formatPercent(run.metrics.max_drawdown)}
          change="From peak"
          changeType="negative"
        />
        <StatsCard
          title="Win Rate"
          value={`${(parseFloat(run.metrics.win_rate) * 100).toFixed(0)}%`}
          change={`${run.metrics.total_trades} trades`}
          changeType={parseFloat(run.metrics.win_rate) >= 0.5 ? "positive" : "negative"}
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="equity">Equity Curve</TabsTrigger>
          <TabsTrigger value="trades">Trades</TabsTrigger>
          <TabsTrigger value="metrics">All Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Performance Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Return</span>
                  <span
                    className={cn(
                      "font-mono font-medium",
                      returnPositive ? "text-profit" : "text-loss"
                    )}
                  >
                    {formatPercent(run.metrics.total_return)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">CAGR</span>
                  <span className="font-mono">
                    {formatPercent(run.metrics.cagr)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Sharpe Ratio</span>
                  <span className="font-mono">{run.metrics.sharpe_ratio}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Sortino Ratio</span>
                  <span className="font-mono">{run.metrics.sortino_ratio}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max Drawdown</span>
                  <span className="font-mono text-loss">
                    {formatPercent(run.metrics.max_drawdown)}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Trading Statistics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Trades</span>
                  <span className="font-mono">{run.metrics.total_trades}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Win Rate</span>
                  <span className="font-mono">
                    {(parseFloat(run.metrics.win_rate) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Profit Factor</span>
                  <span className="font-mono">{run.metrics.profit_factor}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Avg Trade Duration
                  </span>
                  <span className="font-mono">
                    {parseFloat(run.metrics.avg_trade_duration_hours).toFixed(1)}h
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Run Date</span>
                  <span className="font-mono text-sm">
                    {formatDateTime(run.created_at)}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Mini Equity Chart */}
          <EquityChart data={run.equity_curve} title="Portfolio Value" />
        </TabsContent>

        <TabsContent value="equity">
          <EquityChart data={run.equity_curve} title="Portfolio Equity Curve" />
        </TabsContent>

        <TabsContent value="trades">
          <Card>
            <CardHeader>
              <CardTitle>Trade History</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Side</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead className="text-right">Entry</TableHead>
                    <TableHead className="text-right">Exit</TableHead>
                    <TableHead className="text-right">P&L</TableHead>
                    <TableHead className="text-right">Return</TableHead>
                    <TableHead>Entry Time</TableHead>
                    <TableHead>Exit Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {run.trades.map((trade) => {
                    const pnlPositive = parseFloat(trade.pnl) >= 0;
                    return (
                      <TableRow key={trade.trade_id}>
                        <TableCell className="font-medium">
                          {trade.symbol}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={cn(
                              trade.side === "BUY"
                                ? "text-profit"
                                : "text-loss"
                            )}
                          >
                            {trade.side}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {trade.quantity}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          ${parseFloat(trade.entry_price).toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          ${parseFloat(trade.exit_price).toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right">
                          <span
                            className={cn(
                              "font-mono",
                              pnlPositive ? "text-profit" : "text-loss"
                            )}
                          >
                            {formatCurrency(trade.pnl)}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <span
                            className={cn(
                              "font-mono",
                              pnlPositive ? "text-profit" : "text-loss"
                            )}
                          >
                            {formatPercent(trade.pnl_pct)}
                          </span>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDateTime(trade.entry_time)}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDateTime(trade.exit_time)}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="metrics">
          <Card>
            <CardHeader>
              <CardTitle>Complete Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {Object.entries(run.metrics).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex justify-between p-3 rounded-lg bg-muted"
                  >
                    <span className="text-muted-foreground capitalize">
                      {key.replace(/_/g, " ")}
                    </span>
                    <span className="font-mono">{value}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
