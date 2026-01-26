"use client";

import { useStrategy } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatsCard } from "@/components/stats-card";
import { ArrowLeft, Play, Pause, Settings } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { use } from "react";

interface StrategyDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function StrategyDetailPage({ params }: StrategyDetailPageProps) {
  const { id } = use(params);
  const { strategy } = useStrategy(id);

  if (!strategy) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Strategy not found</p>
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

  const pnl = strategy.performance?.total_pnl ?? "0";
  const pnlPositive = parseFloat(pnl) >= 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Link href="/strategies">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-2xl font-bold">{strategy.name}</h2>
              <Badge
                className={cn(
                  strategy.status === "active"
                    ? "bg-profit text-white"
                    : "bg-loss text-white"
                )}
              >
                {strategy.status === "active" ? "Live" : "Stopped"}
              </Badge>
              <Badge variant="outline">{strategy.mode}</Badge>
            </div>
            <p className="text-muted-foreground">{strategy.description}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="gap-2">
            <Settings className="h-4 w-4" />
            Configure
          </Button>
          <Button
            variant={strategy.status === "active" ? "destructive" : "default"}
            size="sm"
            className="gap-2"
          >
            {strategy.status === "active" ? (
              <>
                <Pause className="h-4 w-4" />
                Pause
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Start
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatsCard
          title="Total P&L"
          value={formatCurrency(pnl)}
          change={formatPercent(strategy.performance?.sharpe_ratio ?? "0") + " Sharpe"}
          changeType={pnlPositive ? "positive" : "negative"}
        />
        <StatsCard
          title="Max Drawdown"
          value={formatPercent(strategy.performance?.max_drawdown ?? "0")}
          change="From peak"
          changeType="negative"
        />
        <StatsCard
          title="Win Rate"
          value={`${(parseFloat(strategy.performance?.win_rate ?? "0") * 100).toFixed(0)}%`}
          change="All time"
          changeType="neutral"
        />
        <StatsCard
          title="Max Positions"
          value={strategy.max_positions.toString()}
          change={`Risk: ${strategy.risk_per_trade_pct}%`}
          changeType="neutral"
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Strategy Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Universe Size</span>
                  <span className="font-mono">{strategy.universe_size}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max Positions</span>
                  <span className="font-mono">{strategy.max_positions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Risk Per Trade</span>
                  <span className="font-mono">{strategy.risk_per_trade_pct}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created</span>
                  <span className="font-mono text-sm">
                    {new Date(strategy.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Last Updated</span>
                  <span className="font-mono text-sm">
                    {new Date(strategy.updated_at).toLocaleDateString()}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Performance Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total P&L</span>
                  <span
                    className={cn(
                      "font-mono",
                      pnlPositive ? "text-profit" : "text-loss"
                    )}
                  >
                    {formatCurrency(pnl)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Sharpe Ratio</span>
                  <span className="font-mono">
                    {strategy.performance?.sharpe_ratio ?? "N/A"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max Drawdown</span>
                  <span className="font-mono text-loss">
                    {formatPercent(strategy.performance?.max_drawdown ?? "0")}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Win Rate</span>
                  <span className="font-mono">
                    {((parseFloat(strategy.performance?.win_rate ?? "0") * 100).toFixed(0))}%
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="positions">
          <Card>
            <CardHeader>
              <CardTitle>Open Positions</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground text-center py-8">
                No open positions for this strategy
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config">
          <Card>
            <CardHeader>
              <CardTitle>Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-muted p-4 rounded-lg overflow-auto text-sm font-mono">
                {JSON.stringify(strategy.config || {
                  model_type: "xgboost",
                  features: ["rsi_14", "macd", "volume_sma_20"],
                  signal_threshold: 0.6,
                  stop_loss_pct: "2.0",
                  take_profit_pct: "5.0"
                }, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs">
          <Card>
            <CardHeader>
              <CardTitle>Activity Logs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 font-mono text-sm">
                <div className="flex gap-4 text-muted-foreground">
                  <span>2026-01-25 14:30:00</span>
                  <span>Signal Generated: BUY AAPL @ 150.25</span>
                </div>
                <div className="flex gap-4 text-muted-foreground">
                  <span>2026-01-25 14:30:01</span>
                  <span>Order Submitted: BUY 100 AAPL LIMIT @ 150.25</span>
                </div>
                <div className="flex gap-4 text-muted-foreground">
                  <span>2026-01-25 14:30:05</span>
                  <span className="text-profit">Order Filled: 100 AAPL @ 150.20</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
