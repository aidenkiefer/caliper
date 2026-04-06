"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";

import { HelpHint } from "@/components/help-hint";
import { StatusBadge } from "@/components/status-badge";
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
  FEATURE_FIELD_GROUPS,
  formatFeatureValue,
} from "@/lib/feature-display";
import { ApiHttpError, fetchFeatureHistory, fetchFeatureLatest } from "@/lib/api";
import type { FeatureSnapshot } from "@/lib/types/features";

function defaultRange() {
  const end = new Date();
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  const toLocal = (d: Date) => {
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  return { start: toLocal(start), end: toLocal(end) };
}

export default function FeaturesExplorerPage() {
  const defaults = useMemo(() => defaultRange(), []);
  const [marketId, setMarketId] = useState("");
  const [startLocal, setStartLocal] = useState(defaults.start);
  const [endLocal, setEndLocal] = useState(defaults.end);
  const [limit, setLimit] = useState(100);

  const [latest, setLatest] = useState<FeatureSnapshot | null>(null);
  const [history, setHistory] = useState<FeatureSnapshot[]>([]);
  const [loading, setLoading] = useState<"latest" | "history" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const parseError = useCallback((e: unknown): string => {
    if (e instanceof ApiHttpError) {
      if (e.status === 503) {
        return "API returned 503 — the feature store needs DB_URL on the server (same Postgres URL as the database). See docs/user-guide.md.";
      }
      if (e.status === 404) {
        return "No feature snapshot found for this market_id yet (empty pm.features or wrong id).";
      }
      if (e.status === 422) {
        return "Invalid time range: start must be before end.";
      }
      return `Request failed (${e.status}). ${e.message.slice(0, 200)}`;
    }
    if (e instanceof Error) return e.message;
    return "Unknown error";
  }, []);

  const loadLatest = async () => {
    if (!marketId.trim()) {
      setError("Enter a market_id.");
      return;
    }
    setError(null);
    setLoading("latest");
    try {
      const data = await fetchFeatureLatest(marketId.trim());
      setLatest(data);
    } catch (e) {
      setLatest(null);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  const loadHistory = async () => {
    if (!marketId.trim()) {
      setError("Enter a market_id.");
      return;
    }
    setError(null);
    setLoading("history");
    try {
      const start = new Date(startLocal);
      const end = new Date(endLocal);
      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        throw new Error("Invalid start or end datetime.");
      }
      const data = await fetchFeatureHistory(marketId.trim(), {
        start: start.toISOString(),
        end: end.toISOString(),
        limit,
      });
      setHistory(data);
    } catch (e) {
      setHistory([]);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            Feature snapshots
            <HelpHint helpId="platform-features" label="Feature snapshots explorer" />
          </h2>
          <p className="text-muted-foreground mt-1 text-sm max-w-2xl">
            Read Sprint 12 <code className="text-xs">FeatureSnapshot</code> rows from{" "}
            <code className="text-xs">pm.features</code> via the API. Requires server{" "}
            <code className="text-xs">DB_URL</code>.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status="live" />
          <Button variant="outline" size="sm" asChild>
            <Link href="/platform">Back to platform</Link>
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Query</CardTitle>
          <CardDescription>
            Use the same <code className="text-xs">market_id</code> string your pipeline stores (often a condition or token id).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="sm:col-span-2 lg:col-span-2 space-y-2">
              <label htmlFor="market-id" className="text-sm font-medium">
                market_id
              </label>
              <Input
                id="market-id"
                value={marketId}
                onChange={(e) => setMarketId(e.target.value)}
                placeholder="e.g. condition id or token id"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="hist-start" className="text-sm font-medium">
                History start (local)
              </label>
              <Input
                id="hist-start"
                type="datetime-local"
                value={startLocal}
                onChange={(e) => setStartLocal(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="hist-end" className="text-sm font-medium">
                History end (local)
              </label>
              <Input
                id="hist-end"
                type="datetime-local"
                value={endLocal}
                onChange={(e) => setEndLocal(e.target.value)}
              />
            </div>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-2">
              <label htmlFor="limit" className="text-sm font-medium">
                History limit
              </label>
              <Input
                id="limit"
                type="number"
                min={1}
                max={1000}
                className="w-28"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value) || 100)}
              />
            </div>
            <Button
              type="button"
              onClick={loadLatest}
              disabled={loading !== null}
            >
              {loading === "latest" ? "Loading…" : "Load latest"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={loadHistory}
              disabled={loading !== null}
            >
              {loading === "history" ? "Loading…" : "Load history"}
            </Button>
          </div>
          {error ? (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          ) : null}
        </CardContent>
      </Card>

      {loading === "latest" ? (
        <Skeleton className="h-48 w-full" />
      ) : null}

      {latest && loading !== "latest" ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Latest snapshot</CardTitle>
            <CardDescription>
              Captured {latest.captured_at} · token {latest.token_id}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {FEATURE_FIELD_GROUPS.map((group) => (
              <details
                key={group.id}
                className="rounded-lg border border-border bg-card/50 px-3 py-2"
                open={group.id === "identity" || group.id === "market_state"}
              >
                <summary className="flex cursor-pointer list-none items-center gap-2 py-1 font-medium [&::-webkit-details-marker]:hidden">
                  <span className="min-w-0 flex-1">{group.label}</span>
                  <HelpHint helpId={group.helpId} label={group.label} />
                </summary>
                <dl className="mt-3 grid gap-2 sm:grid-cols-2 text-sm">
                  {group.keys.map((key) => (
                    <div key={key} className="flex flex-col gap-0.5">
                      <dt className="text-muted-foreground font-mono text-xs">
                        {key}
                      </dt>
                      <dd className="font-tabular break-all">
                        {formatFeatureValue(latest[key])}
                      </dd>
                    </div>
                  ))}
                </dl>
              </details>
            ))}
            <details className="rounded-lg border border-dashed px-3 py-2">
              <summary className="flex cursor-pointer list-none items-center gap-2 py-1 text-sm font-medium [&::-webkit-details-marker]:hidden">
                <span className="min-w-0 flex-1">Advanced: raw JSON</span>
                <HelpHint helpId="features-advanced-json" label="Raw JSON" />
              </summary>
              <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs">
                {JSON.stringify(latest, null, 2)}
              </pre>
            </details>
          </CardContent>
        </Card>
      ) : null}

      {loading === "history" ? (
        <Skeleton className="h-64 w-full" />
      ) : null}

      {history.length > 0 && loading !== "history" ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">History ({history.length} rows)</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>captured_at</TableHead>
                  <TableHead>mid_price</TableHead>
                  <TableHead>spread_bps</TableHead>
                  <TableHead>vol_regime</TableHead>
                  <TableHead>staleness</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((row, i) => (
                  <TableRow key={`${row.captured_at}-${i}`}>
                    <TableCell className="font-mono text-xs whitespace-nowrap">
                      {row.captured_at}
                    </TableCell>
                    <TableCell className="font-tabular text-sm">
                      {formatFeatureValue(row.mid_price)}
                    </TableCell>
                    <TableCell className="font-tabular text-sm">
                      {formatFeatureValue(row.spread_bps)}
                    </TableCell>
                    <TableCell>{row.vol_regime}</TableCell>
                    <TableCell>
                      {row.data_staleness_flag ? "stale" : "ok"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
