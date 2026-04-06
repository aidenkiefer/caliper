"use client";

import { useCallback, useMemo, useState } from "react";

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
  ApiHttpError,
  fetchAllocationCurrent,
  fetchAllocationHistory,
  fetchPerformanceMatrix,
  fetchRegimeCurrent,
  fetchRegimeCurrentForMarket,
  fetchRegimeHistory,
} from "@/lib/api";
import type { RegimeStateDto } from "@/lib/types/explorers";

function defaultRange() {
  const end = new Date();
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  const toLocal = (d: Date) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  return { start: toLocal(start), end: toLocal(end) };
}

export default function RegimeAllocationExplorerPage() {
  const defaults = useMemo(() => defaultRange(), []);
  const [marketId, setMarketId] = useState("");

  const [regimeGlobal, setRegimeGlobal] = useState<RegimeStateDto | null>(null);
  const [regimeMarket, setRegimeMarket] = useState<RegimeStateDto | null>(null);
  const [allocation, setAllocation] = useState<unknown | null>(null);
  const [matrix, setMatrix] = useState<unknown | null>(null);
  const [regimeHistory, setRegimeHistory] = useState<RegimeStateDto[]>([]);
  const [allocHistory, setAllocHistory] = useState<unknown[]>([]);

  const [startLocal, setStartLocal] = useState(defaults.start);
  const [endLocal, setEndLocal] = useState(defaults.end);
  const [histLimit, setHistLimit] = useState(100);

  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const parseError = useCallback((e: unknown): string => {
    if (e instanceof ApiHttpError) {
      if (e.status === 503) {
        return "503 — regime/allocation routes need DB_URL on the API host.";
      }
      return `HTTP ${e.status}: ${e.message.slice(0, 240)}`;
    }
    if (e instanceof Error) return e.message;
    return "Unknown error";
  }, []);

  const loadCore = async () => {
    setError(null);
    setLoading("core");
    try {
      const [g, a, m] = await Promise.all([
        fetchRegimeCurrent(),
        fetchAllocationCurrent(),
        fetchPerformanceMatrix(),
      ]);
      setRegimeGlobal(g);
      setAllocation(a);
      setMatrix(m);
      if (marketId.trim()) {
        setRegimeMarket(await fetchRegimeCurrentForMarket(marketId.trim()));
      } else {
        setRegimeMarket(null);
      }
    } catch (e) {
      setRegimeGlobal(null);
      setRegimeMarket(null);
      setAllocation(null);
      setMatrix(null);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  const loadHistory = async () => {
    setError(null);
    setLoading("history");
    try {
      const start = new Date(startLocal);
      const end = new Date(endLocal);
      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        throw new Error("Invalid start or end datetime.");
      }
      const startIso = start.toISOString();
      const endIso = end.toISOString();
      const [rh, ah] = await Promise.all([
        fetchRegimeHistory({
          start: startIso,
          end: endIso,
          market_id: marketId.trim() || undefined,
          limit: histLimit,
        }),
        fetchAllocationHistory({
          start: startIso,
          end: endIso,
          limit: histLimit,
        }),
      ]);
      setRegimeHistory(rh);
      setAllocHistory(ah);
    } catch (e) {
      setRegimeHistory([]);
      setAllocHistory([]);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <ExplorerPageHeader
        title="Regime & allocation"
        helpId="explorer-regime-allocation"
        badges={[
          { status: "live", label: "Live when API has DB_URL and pm.* data" },
        ]}
      />
      <p className="text-sm text-muted-foreground max-w-3xl">
        Reads <code className="text-xs">GET /v1/regime/*</code> and{" "}
        <code className="text-xs">GET /v1/allocation/*</code>. Optional{" "}
        <code className="text-xs">market_id</code> scopes regime current and history.
      </p>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Scope</CardTitle>
          <CardDescription>
            Leave market empty for global regime only; set it to also fetch per-market current.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="space-y-1 min-w-[200px] flex-1">
            <label className="text-xs text-muted-foreground">market_id</label>
            <Input
              placeholder="optional Polymarket market id"
              value={marketId}
              onChange={(e) => setMarketId(e.target.value)}
            />
          </div>
          <Button type="button" onClick={() => void loadCore()} disabled={loading === "core"}>
            Load current + matrix
          </Button>
        </CardContent>
      </Card>

      {loading === "core" ? <Skeleton className="h-48 w-full" /> : null}
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Regime (global)</CardTitle>
          </CardHeader>
          <CardContent>
            {regimeGlobal ? <JsonBlock value={regimeGlobal} /> : (
              <p className="text-sm text-muted-foreground">Not loaded yet.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Regime (market)</CardTitle>
          </CardHeader>
          <CardContent>
            {!marketId.trim() ? (
              <p className="text-sm text-muted-foreground">Enter market_id and reload.</p>
            ) : regimeMarket ? (
              <JsonBlock value={regimeMarket} />
            ) : (
              <p className="text-sm text-muted-foreground">Run “Load current + matrix”.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Allocation (current)</CardTitle>
          </CardHeader>
          <CardContent>
            {allocation != null ? <JsonBlock value={allocation} /> : (
              <p className="text-sm text-muted-foreground">Not loaded yet.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Performance matrix</CardTitle>
          </CardHeader>
          <CardContent>
            {matrix != null ? <JsonBlock value={matrix} /> : (
              <p className="text-sm text-muted-foreground">Not loaded yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">History</CardTitle>
          <CardDescription>
            Uses ISO instants from local datetime (same pattern as feature snapshots). Regime history
            respects optional market_id.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">start (local)</label>
              <Input
                type="datetime-local"
                value={startLocal}
                onChange={(e) => setStartLocal(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">end (local)</label>
              <Input
                type="datetime-local"
                value={endLocal}
                onChange={(e) => setEndLocal(e.target.value)}
              />
            </div>
            <div className="space-y-1 w-24">
              <label className="text-xs text-muted-foreground">limit</label>
              <Input
                type="number"
                min={1}
                max={5000}
                value={histLimit}
                onChange={(e) => setHistLimit(Number(e.target.value) || 100)}
              />
            </div>
            <Button type="button" onClick={() => void loadHistory()} disabled={loading === "history"}>
              Load history
            </Button>
          </div>
          {loading === "history" ? <Skeleton className="h-32 w-full" /> : null}
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <h4 className="text-sm font-medium mb-2">Regime history ({regimeHistory.length})</h4>
              <JsonBlock value={regimeHistory} />
            </div>
            <div>
              <h4 className="text-sm font-medium mb-2">Allocation history ({allocHistory.length})</h4>
              <JsonBlock value={allocHistory} />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
