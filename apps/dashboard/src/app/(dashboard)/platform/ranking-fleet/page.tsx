"use client";

import { useCallback, useEffect, useState } from "react";

import { ExplorerPageHeader } from "@/components/explorer-page-header";
import { JsonBlock } from "@/components/json-block";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ApiHttpError,
  fetchFleetSignals,
  fetchFleetStatus,
  fetchPaperTrades,
  fetchRankedUniverse,
} from "@/lib/api";
import type {
  FleetSignal,
  FleetStatus,
  PaperTrade,
  RankedUniverse,
} from "@/lib/types/models";

export default function RankingFleetExplorerPage() {
  const [ranked, setRanked] = useState<RankedUniverse | null>(null);
  const [fleet, setFleet] = useState<FleetStatus | null>(null);
  const [signals, setSignals] = useState<FleetSignal[]>([]);
  const [paper, setPaper] = useState<PaperTrade[]>([]);
  const [signalLimit, setSignalLimit] = useState(50);
  const [paperLimit, setPaperLimit] = useState(50);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const parseError = useCallback((e: unknown): string => {
    if (e instanceof ApiHttpError) {
      if (e.status === 503) {
        return "503 — ranking/fleet routes are not fully wired yet (ranking output + orchestrator status/signals need persistence; paper trades require DB + migrations).";
      }
      return `HTTP ${e.status}: ${e.message.slice(0, 240)}`;
    }
    if (e instanceof Error) return e.message;
    return "Unknown error";
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, f, s, p] = await Promise.all([
        fetchRankedUniverse(),
        fetchFleetStatus(),
        fetchFleetSignals({ limit: signalLimit }),
        fetchPaperTrades({ limit: paperLimit }),
      ]);
      setRanked(r);
      setFleet(f);
      setSignals(s);
      setPaper(p);
    } catch (e) {
      setRanked(null);
      setFleet(null);
      setSignals([]);
      setPaper([]);
      setError(parseError(e));
    } finally {
      setLoading(false);
    }
  }, [parseError, signalLimit, paperLimit]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const selected = ranked?.selected_markets ?? [];
  const candidates = ranked?.candidate_markets ?? [];

  return (
    <div className="space-y-6">
      <ExplorerPageHeader
        title="Ranking & paper fleet"
        helpId="explorer-ranking-fleet"
        badges={[
          { status: "mock", label: "REST often returns mock JSON until handlers use pm.*" },
        ]}
      />
      <p className="text-sm text-muted-foreground max-w-3xl">
        <code className="text-xs">GET /v1/ranking/current</code>,{" "}
        <code className="text-xs">/fleet/status</code>,{" "}
        <code className="text-xs">/fleet/signals</code>,{" "}
        <code className="text-xs">/fleet/paper-trades</code>.
      </p>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Reload</CardTitle>
          <CardDescription>Adjust limits and refetch all four endpoints.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 items-end">
          <div className="space-y-1 w-24">
            <label className="text-xs text-muted-foreground">signals limit</label>
            <Input
              type="number"
              min={1}
              max={500}
              value={signalLimit}
              onChange={(e) => setSignalLimit(Number(e.target.value) || 50)}
            />
          </div>
          <div className="space-y-1 w-24">
            <label className="text-xs text-muted-foreground">paper limit</label>
            <Input
              type="number"
              min={1}
              max={500}
              value={paperLimit}
              onChange={(e) => setPaperLimit(Number(e.target.value) || 50)}
            />
          </div>
          <Button type="button" onClick={() => void loadAll()} disabled={loading}>
            Refresh
          </Button>
        </CardContent>
      </Card>

      {loading ? <Skeleton className="h-48 w-full" /> : null}
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      {ranked && !loading ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ranked universe</CardTitle>
            <CardDescription className="font-mono text-xs">
              ranked_at {ranked.ranked_at} · method {ranked.ranking_method} · candidates{" "}
              {ranked.total_candidates}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 overflow-x-auto">
            <div>
              <h4 className="text-sm font-medium mb-2">Selected ({selected.length})</h4>
              {selected.length === 0 ? (
                <p className="text-sm text-muted-foreground">None in payload.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Market</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead className="text-right">Score</TableHead>
                      <TableHead className="text-right">EV adj</TableHead>
                      <TableHead>Sel</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selected.map((m) => (
                      <TableRow key={`${m.market_id}-${m.side}`}>
                        <TableCell className="max-w-[200px] truncate font-mono text-xs">
                          {m.market_name || m.market_id}
                        </TableCell>
                        <TableCell>{m.side}</TableCell>
                        <TableCell className="text-right font-tabular">{m.score}</TableCell>
                        <TableCell className="text-right font-tabular">{m.ev_adj}</TableCell>
                        <TableCell>{m.selected ? "yes" : "no"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
            <div>
              <h4 className="text-sm font-medium mb-2">Top candidates ({candidates.length})</h4>
              {candidates.length === 0 ? (
                <p className="text-sm text-muted-foreground">Empty.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Market</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead className="text-right">Score</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {candidates.slice(0, 25).map((m) => (
                      <TableRow key={`c-${m.market_id}-${m.side}`}>
                        <TableCell className="max-w-[200px] truncate font-mono text-xs">
                          {m.market_name || m.market_id}
                        </TableCell>
                        <TableCell>{m.side}</TableCell>
                        <TableCell className="text-right font-tabular">{m.score}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
            <details className="text-sm">
              <summary className="cursor-pointer text-muted-foreground">Raw JSON</summary>
              <JsonBlock value={ranked} />
            </details>
          </CardContent>
        </Card>
      ) : null}

      {fleet && !loading ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Fleet status</CardTitle>
            <CardDescription className="font-mono text-xs">
              {fleet.generated_at} · regime {fleet.current_regime} · mode {fleet.current_mode}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {fleet.strategies.length === 0 ? (
              <p className="text-sm text-muted-foreground">No strategy cards.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Strategy</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Regime</TableHead>
                    <TableHead className="text-right">PnL 24h</TableHead>
                    <TableHead className="text-right">Sharpe 7d</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {fleet.strategies.map((s) => (
                    <TableRow key={s.strategy_id}>
                      <TableCell className="font-mono text-xs">{s.strategy_id}</TableCell>
                      <TableCell>{s.status}</TableCell>
                      <TableCell>{s.current_regime}</TableCell>
                      <TableCell className="text-right font-tabular">{s.pnl_24h_usd}</TableCell>
                      <TableCell className="text-right font-tabular">{s.sharpe_7d}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            <details className="text-sm">
              <summary className="cursor-pointer text-muted-foreground">Raw JSON</summary>
              <JsonBlock value={fleet} />
            </details>
          </CardContent>
        </Card>
      ) : null}

      {!loading && !error && fleet ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent signals</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {signals.length === 0 ? (
              <p className="text-sm text-muted-foreground">No signal rows in this response.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Strategy</TableHead>
                    <TableHead>Market</TableHead>
                    <TableHead>Dir</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Regime</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {signals.map((sig) => (
                    <TableRow key={sig.signal_id}>
                      <TableCell className="text-xs whitespace-nowrap">{sig.timestamp}</TableCell>
                      <TableCell className="font-mono text-xs">{sig.strategy_id}</TableCell>
                      <TableCell className="font-mono text-xs max-w-[140px] truncate">{sig.market_id}</TableCell>
                      <TableCell>{sig.direction}</TableCell>
                      <TableCell>{sig.action_taken}</TableCell>
                      <TableCell>{sig.regime}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : null}

      {!loading && !error && ranked ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Paper trades</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {paper.length === 0 ? (
              <p className="text-sm text-muted-foreground">No paper trade rows in this response.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Strategy</TableHead>
                    <TableHead>Market</TableHead>
                    <TableHead>Side</TableHead>
                    <TableHead className="text-right">Price</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead className="text-right">Notional</TableHead>
                    <TableHead className="text-right">Conf</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paper.map((t) => (
                    <TableRow key={t.trade_id}>
                      <TableCell className="text-xs whitespace-nowrap">{t.executed_at}</TableCell>
                      <TableCell className="font-mono text-xs">{t.strategy_id}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{t.market_id}</TableCell>
                      <TableCell>{t.side}</TableCell>
                      <TableCell className="text-right font-tabular">{t.price}</TableCell>
                      <TableCell className="text-right font-tabular">{t.quantity}</TableCell>
                      <TableCell className="text-right font-tabular">{t.notional}</TableCell>
                      <TableCell className="text-right font-tabular">{t.confidence.toFixed(2)}</TableCell>
                      <TableCell>{t.status}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
