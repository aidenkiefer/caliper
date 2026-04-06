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
import type { FleetSignal } from "@/lib/types/models";

function confidenceBadgeClass(confidence: number) {
  if (confidence >= 0.8) return "bg-emerald-500 hover:bg-emerald-500";
  if (confidence >= 0.6) return "bg-amber-500 hover:bg-amber-500";
  return "bg-slate-500 hover:bg-slate-500";
}

export function SignalLog({ signals }: { signals: FleetSignal[] }) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Per-Strategy Signal Log</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Strategy</TableHead>
              <TableHead>Market</TableHead>
              <TableHead>Direction</TableHead>
              <TableHead className="text-right">Confidence</TableHead>
              <TableHead>Action</TableHead>
              <TableHead className="text-right">Fill</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {signals.slice(0, 50).map((signal) => (
              <TableRow key={signal.signal_id}>
                <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                  {new Date(signal.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </TableCell>
                <TableCell className="font-medium">{signal.strategy_id}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{signal.market_id}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="capitalize">
                    {signal.direction}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Badge className={confidenceBadgeClass(signal.confidence)}>
                    {(signal.confidence * 100).toFixed(0)}%
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="capitalize">
                    {signal.action_taken}
                  </Badge>
                </TableCell>
                <TableCell className="text-right font-tabular">
                  {signal.fill_price == null ? "—" : signal.fill_price.toFixed(3)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

