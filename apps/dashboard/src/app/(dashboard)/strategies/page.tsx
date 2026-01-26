"use client";

import Link from "next/link";
import { useStrategies } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Settings, Eye, Pause, Play } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

const statusConfig = {
  active: { label: "Live", color: "bg-profit text-white" },
  inactive: { label: "Stopped", color: "bg-loss text-white" },
};

const modeConfig = {
  LIVE: { label: "Live", color: "bg-profit" },
  PAPER: { label: "Paper", color: "bg-warning" },
  BACKTEST: { label: "Backtest", color: "bg-muted" },
};

export default function StrategiesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const { strategies } = useStrategies(
    statusFilter !== "all" ? { status: statusFilter } : undefined
  );

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold">Strategies</h2>
          <p className="text-muted-foreground">
            Manage and monitor your trading strategies
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Filter status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>Strategy Fleet</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead className="text-right">Performance (30d)</TableHead>
                <TableHead className="text-right">Drawdown</TableHead>
                <TableHead className="text-right">Win Rate</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {strategies.map((strategy) => {
                const status = statusConfig[strategy.status];
                const mode = modeConfig[strategy.mode];
                const pnl = strategy.performance?.total_pnl ?? "0";
                const pnlPositive = parseFloat(pnl) >= 0;
                const drawdown = strategy.performance?.max_drawdown ?? "0";

                return (
                  <TableRow key={strategy.strategy_id}>
                    <TableCell>
                      <Badge className={cn("text-xs", status.color)}>
                        {status.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div>
                        <div className="font-medium">{strategy.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {strategy.description.slice(0, 50)}...
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn("text-xs")}>
                        {mode.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <span
                        className={cn(
                          "font-mono",
                          pnlPositive ? "text-profit" : "text-loss"
                        )}
                      >
                        {formatCurrency(pnl)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="font-mono text-loss">
                        {formatPercent(drawdown)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="font-mono">
                        {((parseFloat(strategy.performance?.win_rate ?? "0") * 100).toFixed(0))}%
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          title={strategy.status === "active" ? "Pause" : "Start"}
                        >
                          {strategy.status === "active" ? (
                            <Pause className="h-4 w-4" />
                          ) : (
                            <Play className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          title="Settings"
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                        <Link href={`/strategies/${strategy.strategy_id}`}>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            title="View"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </Link>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
