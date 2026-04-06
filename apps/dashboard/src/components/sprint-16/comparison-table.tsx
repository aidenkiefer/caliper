"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { StrategyComparisonRow } from "@/lib/types/models";

function formatSignedPercent(value: number) {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

export function ComparisonTable({ rows }: { rows: StrategyComparisonRow[] }) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Cross-Strategy Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Strategy</TableHead>
              <TableHead>Baseline</TableHead>
              <TableHead className="text-right">Sharpe</TableHead>
              <TableHead className="text-right">Sortino</TableHead>
              <TableHead className="text-right">Win Rate</TableHead>
              <TableHead className="text-right">Max DD</TableHead>
              <TableHead className="text-right">Profit Factor</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.strategy_id}>
                <TableCell className="font-medium">{row.strategy_id}</TableCell>
                <TableCell>
                  <Badge variant="outline">{row.baseline}</Badge>
                </TableCell>
                <TableCell className="text-right font-tabular">{row.sharpe_7d.toFixed(2)}</TableCell>
                <TableCell className="text-right font-tabular">{row.sortino_7d.toFixed(2)}</TableCell>
                <TableCell className="text-right font-tabular">{formatSignedPercent(row.win_rate)}</TableCell>
                <TableCell className="text-right font-tabular">{formatSignedPercent(row.max_drawdown)}</TableCell>
                <TableCell className="text-right font-tabular">{row.profit_factor.toFixed(2)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

