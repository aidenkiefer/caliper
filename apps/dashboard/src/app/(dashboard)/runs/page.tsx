"use client";

import Link from "next/link";
import { useRuns } from "@/lib/hooks";
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
import { Eye, Plus, RefreshCw, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

const statusConfig = {
  RUNNING: { label: "Running", icon: Loader2, color: "text-warning" },
  COMPLETED: { label: "Completed", icon: CheckCircle, color: "text-profit" },
  FAILED: { label: "Failed", icon: XCircle, color: "text-loss" },
};

const typeConfig = {
  BACKTEST: { label: "Backtest", color: "bg-muted" },
  PAPER: { label: "Paper", color: "bg-warning/20 text-warning" },
  LIVE: { label: "Live", color: "bg-profit/20 text-profit" },
};

export default function RunsPage() {
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { runs } = useRuns({
    run_type: typeFilter !== "all" ? typeFilter : undefined,
    status: statusFilter !== "all" ? statusFilter : undefined,
  });

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold">Runs</h2>
          <p className="text-muted-foreground">
            View backtest and trading session history
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Filter type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="BACKTEST">Backtest</SelectItem>
              <SelectItem value="PAPER">Paper</SelectItem>
              <SelectItem value="LIVE">Live</SelectItem>
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Filter status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="RUNNING">Running</SelectItem>
              <SelectItem value="COMPLETED">Completed</SelectItem>
              <SelectItem value="FAILED">Failed</SelectItem>
            </SelectContent>
          </Select>
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            New Backtest
          </Button>
        </div>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>Run History</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Strategy</TableHead>
                <TableHead>Date Range</TableHead>
                <TableHead className="text-right">Return</TableHead>
                <TableHead className="text-right">Sharpe</TableHead>
                <TableHead className="text-right">Drawdown</TableHead>
                <TableHead className="text-right">Trades</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run) => {
                const status = statusConfig[run.status];
                const type = typeConfig[run.run_type];
                const StatusIcon = status.icon;
                const returnPositive = parseFloat(run.total_return) >= 0;

                return (
                  <TableRow key={run.run_id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <StatusIcon
                          className={cn(
                            "h-4 w-4",
                            status.color,
                            run.status === "RUNNING" && "animate-spin"
                          )}
                        />
                        <span className="text-sm">{status.label}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={cn("text-xs", type.color)}>
                        {type.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="font-medium">{run.strategy_id}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {formatDate(run.start_date)} - {formatDate(run.end_date)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span
                        className={cn(
                          "font-mono",
                          returnPositive ? "text-profit" : "text-loss"
                        )}
                      >
                        {formatPercent(run.total_return)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="font-mono">{run.sharpe_ratio}</span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="font-mono text-loss">
                        {formatPercent(run.max_drawdown)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="font-mono">{run.total_trades}</span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        {run.status === "RUNNING" && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            title="Refresh"
                          >
                            <RefreshCw className="h-4 w-4" />
                          </Button>
                        )}
                        <Link href={`/runs/${run.run_id}`}>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            title="View Report"
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
