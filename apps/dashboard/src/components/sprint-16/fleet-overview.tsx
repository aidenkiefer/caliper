"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { FleetStatus } from "@/lib/types/models";

function formatPercent(value: number) {
  return `${(value * 100).toFixed(0)}%`;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function statusTone(status: string) {
  if (status === "active") return "bg-emerald-500";
  if (status === "cooldown") return "bg-amber-500";
  if (status === "abstain") return "bg-slate-500";
  return "bg-blue-500";
}

export function FleetOverview({ fleetStatus }: { fleetStatus: FleetStatus }) {
  return (
    <Card className="h-full">
      <CardHeader className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Fleet Overview</CardTitle>
          <Badge variant="outline">{fleetStatus.current_mode.toUpperCase()}</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Current regime {fleetStatus.current_regime ?? "—"} • {fleetStatus.strategies.length} strategies
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          {fleetStatus.strategies.map((strategy) => (
            <Card key={strategy.strategy_id} className="border-dashed">
              <CardContent className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold">{strategy.name}</div>
                    <div className="text-xs text-muted-foreground">{strategy.strategy_id}</div>
                  </div>
                  <Badge variant="outline" className="capitalize">
                    {strategy.status}
                  </Badge>
                </div>
                <div className="space-y-2 text-sm">
                  <Row
                    label="PnL 24h"
                    value={strategy.pnl_24h_usd == null ? "—" : formatCurrency(strategy.pnl_24h_usd)}
                  />
                  <Row
                    label="Sharpe 7d"
                    value={strategy.sharpe_7d == null ? "—" : strategy.sharpe_7d.toFixed(2)}
                  />
                  <Row
                    label="Fill rate"
                    value={strategy.fill_rate == null ? "—" : formatPercent(strategy.fill_rate)}
                  />
                  <Row
                    label="Allocation"
                    value={strategy.allocation_weight == null ? "—" : formatPercent(strategy.allocation_weight)}
                  />
                  <Row
                    label="Alignment"
                    value={strategy.regime_alignment == null ? "—" : formatPercent(strategy.regime_alignment)}
                  />
                  <Row
                    label="Signals 24h"
                    value={strategy.signal_count_24h == null ? "—" : strategy.signal_count_24h.toString()}
                  />
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className={`h-full rounded-full ${statusTone(strategy.status)}`}
                    style={{ width: `${Math.max(4, (strategy.allocation_weight ?? 0) * 100)}%` }}
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium font-tabular">{value}</span>
    </div>
  );
}
