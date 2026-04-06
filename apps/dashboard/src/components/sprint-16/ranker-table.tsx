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
import type { RankedUniverse } from "@/lib/types/models";

function formatPercent(value: number) {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

function formatUsd(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatStaleness(rankedAt: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(rankedAt).getTime()) / 1000));
  return `${seconds}s ago`;
}

export function RankerTable({ universe }: { universe: RankedUniverse }) {
  const markets = universe.candidate_markets.length > 0 ? universe.candidate_markets : universe.selected_markets;

  return (
    <Card className="h-full">
      <CardHeader className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Market Ranker</CardTitle>
          <Badge variant="outline">{formatStaleness(universe.ranked_at)}</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          {universe.total_candidates} candidates • {universe.selected_markets.length} selected • {universe.ranking_method}
        </p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Market</TableHead>
              <TableHead className="text-right">Score</TableHead>
              <TableHead className="text-right">Adj EV</TableHead>
              <TableHead className="text-right">Feasibility</TableHead>
              <TableHead className="text-right">Spread</TableHead>
              <TableHead className="text-right">Volume</TableHead>
              <TableHead className="text-right">Selected</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {markets.map((market) => (
              <TableRow key={market.market_id} className={market.selected ? "bg-muted/40" : ""}>
                <TableCell>
                  <div className="space-y-1">
                    <div className="font-medium">{market.market_name}</div>
                    <div className="text-xs text-muted-foreground">
                      {market.market_id} • {market.side} • {market.time_to_close_seconds}s
                    </div>
                  </div>
                </TableCell>
                <TableCell className="text-right font-tabular">{market.score.toFixed(2)}</TableCell>
                <TableCell className="text-right font-tabular">{formatPercent(market.ev_adj)}</TableCell>
                <TableCell className="text-right font-tabular">{formatPercent(market.feasibility)}</TableCell>
                <TableCell className="text-right font-tabular">{formatPercent(market.spread_pct)}</TableCell>
                <TableCell className="text-right font-tabular">{formatUsd(market.volume_24h_usd)}</TableCell>
                <TableCell className="text-right">
                  {market.selected ? (
                    <Badge className="bg-emerald-500 hover:bg-emerald-500">Yes</Badge>
                  ) : (
                    <Badge variant="outline">No</Badge>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-sm text-muted-foreground">Cooldown protected:</span>
          {universe.cooldown_protected.length > 0 ? (
            universe.cooldown_protected.map((marketId) => (
              <Badge key={marketId} variant="secondary">
                {marketId}
              </Badge>
            ))
          ) : (
            <Badge variant="outline">None</Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

