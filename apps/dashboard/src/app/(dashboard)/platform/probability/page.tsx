"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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
  fetchProbabilityCalibration,
  fetchProbabilityHistory,
  fetchProbabilityLagTests,
  fetchProbabilityLatest,
  postProbabilityTrain,
} from "@/lib/api";

function defaultRange() {
  const end = new Date();
  const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  const toLocal = (d: Date) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  return { start: toLocal(start), end: toLocal(end) };
}

export default function ProbabilityExplorerPage() {
  const trainDefaults = useMemo(() => defaultRange(), []);
  const [calibration, setCalibration] = useState<unknown | null>(null);
  const [lag, setLag] = useState<unknown | null>(null);
  const [modelVersion, setModelVersion] = useState("");

  const [marketId, setMarketId] = useState("");
  const [latest, setLatest] = useState<unknown | null>(null);
  const [history, setHistory] = useState<unknown[]>([]);
  const [histStart, setHistStart] = useState(trainDefaults.start);
  const [histEnd, setHistEnd] = useState(trainDefaults.end);

  const [trainMarket, setTrainMarket] = useState("");
  const [modelType, setModelType] = useState("logistic");
  const [trainStart, setTrainStart] = useState(trainDefaults.start);
  const [trainEnd, setTrainEnd] = useState(trainDefaults.end);
  const [trainResult, setTrainResult] = useState<unknown | null>(null);

  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const parseError = useCallback((e: unknown): string => {
    if (e instanceof ApiHttpError) {
      return `HTTP ${e.status}: ${e.message.slice(0, 240)}`;
    }
    if (e instanceof Error) return e.message;
    return "Unknown error";
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
      setLoading("global");
      try {
        const [c, l] = await Promise.all([
          fetchProbabilityCalibration(undefined),
          fetchProbabilityLagTests(),
        ]);
        if (!cancelled) {
          setCalibration(c);
          setLag(l);
        }
      } catch (e) {
        if (!cancelled) {
          setCalibration(null);
          setLag(null);
          setError(parseError(e));
        }
      } finally {
        if (!cancelled) setLoading(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [parseError]);

  const reloadCalibration = async () => {
    setError(null);
    setLoading("global");
    try {
      const v = modelVersion.trim() || undefined;
      const [c, l] = await Promise.all([
        fetchProbabilityCalibration(v),
        fetchProbabilityLagTests(),
      ]);
      setCalibration(c);
      setLag(l);
    } catch (e) {
      setCalibration(null);
      setLag(null);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  const loadLatest = async () => {
    if (!marketId.trim()) {
      setError("Enter market_id for latest.");
      return;
    }
    setError(null);
    setLoading("latest");
    try {
      setLatest(await fetchProbabilityLatest(marketId.trim()));
    } catch (e) {
      setLatest(null);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  const loadHistory = async () => {
    if (!marketId.trim()) {
      setError("Enter market_id for history.");
      return;
    }
    setError(null);
    setLoading("history");
    try {
      const start = new Date(histStart);
      const end = new Date(histEnd);
      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        throw new Error("Invalid history range.");
      }
      const rows = await fetchProbabilityHistory(marketId.trim(), {
        start: start.toISOString(),
        end: end.toISOString(),
      });
      setHistory(rows);
    } catch (e) {
      setHistory([]);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  const runTrain = async () => {
    if (!trainMarket.trim()) {
      setError("Train: enter market_id.");
      return;
    }
    setError(null);
    setLoading("train");
    try {
      const start = new Date(trainStart);
      const end = new Date(trainEnd);
      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        throw new Error("Invalid train window.");
      }
      const res = await postProbabilityTrain({
        market_id: trainMarket.trim(),
        model_type: modelType.trim() || "logistic",
        start: start.toISOString(),
        end: end.toISOString(),
      });
      setTrainResult(res);
    } catch (e) {
      setTrainResult(null);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <ExplorerPageHeader
        title="BTC probability model"
        helpId="explorer-probability"
        badges={[{ status: "stub", label: "Partial mock / stub per Sprint 14" }]}
      />
      <p className="text-sm text-muted-foreground max-w-3xl">
        Endpoints under <code className="text-xs">/v1/probability/*</code>. Calibration and lag tests load on page open;
        latest/history need a <code className="text-xs">market_id</code>.
      </p>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Calibration refresh</CardTitle>
          <CardDescription>Optional filter by model_version query param.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 items-end">
          <div className="space-y-1 min-w-[180px]">
            <label className="text-xs text-muted-foreground">model_version</label>
            <Input
              placeholder="optional"
              value={modelVersion}
              onChange={(e) => setModelVersion(e.target.value)}
            />
          </div>
          <Button type="button" variant="outline" onClick={() => void reloadCalibration()} disabled={!!loading}>
            Reload calibration + lag
          </Button>
        </CardContent>
      </Card>

      {loading === "global" ? <Skeleton className="h-40 w-full" /> : null}
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Calibration</CardTitle>
          </CardHeader>
          <CardContent>
            {calibration != null ? <JsonBlock value={calibration} /> : (
              <p className="text-sm text-muted-foreground">Loading…</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Lag tests</CardTitle>
          </CardHeader>
          <CardContent>
            {lag != null ? <JsonBlock value={lag} /> : (
              <p className="text-sm text-muted-foreground">Loading…</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Latest & history</CardTitle>
          <CardDescription>
            <code className="text-xs">GET /probability/{"{market_id}"}/latest</code> and{" "}
            <code className="text-xs">/history</code>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1 min-w-[220px] flex-1">
              <label className="text-xs text-muted-foreground">market_id</label>
              <Input value={marketId} onChange={(e) => setMarketId(e.target.value)} />
            </div>
            <Button type="button" onClick={() => void loadLatest()} disabled={loading === "latest"}>
              Latest
            </Button>
          </div>
          {loading === "latest" ? <Skeleton className="h-24 w-full" /> : null}
          {latest != null ? <JsonBlock value={latest} /> : null}

          <div className="flex flex-wrap gap-3 items-end pt-2 border-t">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">start</label>
              <Input type="datetime-local" value={histStart} onChange={(e) => setHistStart(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">end</label>
              <Input type="datetime-local" value={histEnd} onChange={(e) => setHistEnd(e.target.value)} />
            </div>
            <Button type="button" variant="secondary" onClick={() => void loadHistory()} disabled={loading === "history"}>
              History
            </Button>
          </div>
          {loading === "history" ? <Skeleton className="h-24 w-full" /> : null}
          {history.length > 0 ? <JsonBlock value={history} /> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Train (POST)</CardTitle>
          <CardDescription>
            <code className="text-xs">POST /v1/probability/train</code> — may return accepted job metadata only.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">market_id</label>
              <Input value={trainMarket} onChange={(e) => setTrainMarket(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">model_type</label>
              <Input value={modelType} onChange={(e) => setModelType(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">start</label>
              <Input type="datetime-local" value={trainStart} onChange={(e) => setTrainStart(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">end</label>
              <Input type="datetime-local" value={trainEnd} onChange={(e) => setTrainEnd(e.target.value)} />
            </div>
          </div>
          <Button type="button" onClick={() => void runTrain()} disabled={loading === "train"}>
            Submit train
          </Button>
          {trainResult != null ? <JsonBlock value={trainResult} /> : null}
        </CardContent>
      </Card>
    </div>
  );
}
