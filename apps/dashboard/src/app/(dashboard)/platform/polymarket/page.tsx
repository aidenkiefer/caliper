"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { ExplorerPageHeader } from "@/components/explorer-page-header";
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
import { ApiHttpError, listPolymarketSessions } from "@/lib/api";
import type { PolymarketSessionListResponse } from "@/lib/types/explorers";

export default function PolymarketSessionsPage() {
  const [data, setData] = useState<PolymarketSessionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [regime, setRegime] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listPolymarketSessions({
        page,
        page_size: 20,
        status: status || undefined,
        regime: regime || undefined,
      });
      setData(res);
    } catch (e) {
      setData(null);
      setError(
        e instanceof ApiHttpError
          ? `HTTP ${e.status}: ${e.message.slice(0, 300)}`
          : e instanceof Error
            ? e.message
            : "Failed to load"
      );
    } finally {
      setLoading(false);
    }
  }, [page, status, regime]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <ExplorerPageHeader
        title="Polymarket sessions"
        helpId="explorer-polymarket"
        badges={[
          { status: "stub", label: "API may be stub or empty until DB pool wired" },
        ]}
      />
      <p className="text-sm text-muted-foreground max-w-3xl">
        Data comes from <code className="text-xs">GET /v1/polymarket/sessions</code>. When the list is empty, run a bot session or wire the API to{" "}
        <code className="text-xs">pm.sessions</code>.
      </p>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Filters</CardTitle>
          <CardDescription>Optional query params on the list endpoint.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">status</label>
            <Input
              placeholder="active | completed | failed"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">volatility_regime</label>
            <Input
              placeholder="regime filter"
              value={regime}
              onChange={(e) => setRegime(e.target.value)}
            />
          </div>
          <Button type="button" onClick={() => { setPage(1); void load(); }}>
            Apply
          </Button>
        </CardContent>
      </Card>

      {loading ? <Skeleton className="h-64 w-full" /> : null}
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      {data && !loading ? (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">
              Sessions ({data.total} total, page {data.page})
            </CardTitle>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Prev
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={page * data.page_size >= data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {data.sessions.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                No sessions returned. This is expected for a fresh API stub.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Session</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Window</TableHead>
                    <TableHead>PnL USDC</TableHead>
                    <TableHead className="text-right">Open</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.sessions.map((s) => (
                    <TableRow key={s.session_id}>
                      <TableCell className="font-mono text-xs max-w-[200px] truncate">
                        {s.session_id}
                      </TableCell>
                      <TableCell>{s.status}</TableCell>
                      <TableCell className="text-xs whitespace-nowrap">
                        {s.window_start?.slice(0, 16)} → {s.window_end?.slice(0, 16)}
                      </TableCell>
                      <TableCell className="font-tabular text-sm">
                        {s.realized_pnl_usdc}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="link" className="h-auto p-0" asChild>
                          <Link href={`/platform/polymarket/${s.session_id}`}>
                            Detail
                          </Link>
                        </Button>
                      </TableCell>
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
