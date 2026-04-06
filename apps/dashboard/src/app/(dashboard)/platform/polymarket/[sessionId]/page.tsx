"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ExplorerPageHeader } from "@/components/explorer-page-header";
import { HelpHint } from "@/components/help-hint";
import { JsonBlock } from "@/components/json-block";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ApiHttpError,
  getPolymarketSession,
  listPolymarketSessionFills,
  listPolymarketSessionOrders,
} from "@/lib/api";
import type {
  PolymarketFillRow,
  PolymarketOrderRow,
  PolymarketSessionRow,
} from "@/lib/types/explorers";

export default function PolymarketSessionDetailPage() {
  const params = useParams();
  const sessionId = typeof params.sessionId === "string" ? params.sessionId : "";

  const [session, setSession] = useState<PolymarketSessionRow | null>(null);
  const [orders, setOrders] = useState<PolymarketOrderRow[] | null>(null);
  const [fills, setFills] = useState<PolymarketFillRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const s = await getPolymarketSession(sessionId);
        if (!cancelled) setSession(s);
      } catch (e) {
        if (!cancelled) {
          setSession(null);
          setError(
            e instanceof ApiHttpError
              ? e.status === 404
                ? "Session not found (API stub or invalid id)."
                : `HTTP ${e.status}: ${e.message.slice(0, 200)}`
              : "Failed to load session"
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const loadOrders = async () => {
    if (!sessionId) return;
    try {
      const o = await listPolymarketSessionOrders(sessionId);
      setOrders(o);
    } catch {
      setOrders([]);
    }
  };

  const loadFills = async () => {
    if (!sessionId) return;
    try {
      const f = await listPolymarketSessionFills(sessionId);
      setFills(f);
    } catch {
      setFills([]);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <ExplorerPageHeader
          title="Polymarket session"
          helpId="explorer-polymarket-session"
          badges={[{ status: "stub", label: "Detail often 404 until DB wired" }]}
        />
        <Button variant="outline" size="sm" asChild>
          <Link href="/platform/polymarket">All sessions</Link>
        </Button>
      </div>
      <p className="font-mono text-xs text-muted-foreground break-all">{sessionId}</p>

      {loading ? <Skeleton className="h-40 w-full" /> : null}
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      {session && !loading ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              Summary
              <HelpHint helpId="explorer-polymarket-session" label="Session summary" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <JsonBlock value={session} />
          </CardContent>
        </Card>
      ) : null}

      <Tabs
        defaultValue="orders"
        onValueChange={(v) => {
          if (v === "orders" && orders === null) void loadOrders();
          if (v === "fills" && fills === null) void loadFills();
        }}
      >
        <TabsList>
          <TabsTrigger value="orders">Orders</TabsTrigger>
          <TabsTrigger value="fills">Fills</TabsTrigger>
        </TabsList>
        <TabsContent value="orders" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {orders === null ? (
                <p className="text-sm text-muted-foreground">Open this tab to load orders.</p>
              ) : orders.length === 0 ? (
                <p className="text-sm text-muted-foreground">No orders (stub or empty).</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Side</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Placed</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orders.map((o) => (
                      <TableRow key={o.order_id}>
                        <TableCell>{o.side}</TableCell>
                        <TableCell className="font-tabular">{o.price}</TableCell>
                        <TableCell className="font-tabular">{o.size}</TableCell>
                        <TableCell>{o.status}</TableCell>
                        <TableCell className="text-xs">{o.placed_at}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="fills" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {fills === null ? (
                <p className="text-sm text-muted-foreground">Open this tab to load fills.</p>
              ) : fills.length === 0 ? (
                <p className="text-sm text-muted-foreground">No fills (stub or empty).</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Side</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead>Fee</TableHead>
                      <TableHead>Adverse</TableHead>
                      <TableHead>Filled</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {fills.map((f) => (
                      <TableRow key={f.fill_id}>
                        <TableCell>{f.side}</TableCell>
                        <TableCell className="font-tabular">{f.price}</TableCell>
                        <TableCell className="font-tabular">{f.size}</TableCell>
                        <TableCell className="font-tabular">{f.fee_paid}</TableCell>
                        <TableCell>
                          {f.adverse_selection_flag === null
                            ? "—"
                            : f.adverse_selection_flag
                              ? "yes"
                              : "no"}
                        </TableCell>
                        <TableCell className="text-xs">{f.filled_at}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
