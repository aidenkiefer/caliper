"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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
import { Textarea } from "@/components/ui/textarea";
import {
  ApiHttpError,
  fetchEvaluationCompare,
  fetchEvaluationLatest,
  fetchEvaluationRegimes,
  fetchSimulationResult,
  postSimulationRun,
} from "@/lib/api";
import type { SimulationRunBody } from "@/lib/types/explorers";

function defaultWindow() {
  const end = new Date();
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  const toLocal = (d: Date) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  return { start: toLocal(start), end: toLocal(end) };
}

export default function SimulationExplorerPage() {
  const win = useMemo(() => defaultWindow(), []);
  const [strategyId, setStrategyId] = useState("");
  const [marketId, setMarketId] = useState("");
  const [tokenId, setTokenId] = useState("");
  const [startLocal, setStartLocal] = useState(win.start);
  const [endLocal, setEndLocal] = useState(win.end);
  const [configText, setConfigText] = useState("");

  const [runAccept, setRunAccept] = useState<{ run_id: string; status: string } | null>(null);
  const [simResult, setSimResult] = useState<unknown | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);

  const [compareIds, setCompareIds] = useState("");
  const [compareOut, setCompareOut] = useState<unknown | null>(null);
  const [evalStrategyId, setEvalStrategyId] = useState("");
  const [evalLatest, setEvalLatest] = useState<unknown | null>(null);
  const [evalRegimes, setEvalRegimes] = useState<unknown[]>([]);

  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const parseError = useCallback((e: unknown): string => {
    if (e instanceof ApiHttpError) {
      return `HTTP ${e.status}: ${e.message.slice(0, 240)}`;
    }
    if (e instanceof Error) return e.message;
    return "Unknown error";
  }, []);

  const stopPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPoll(), [stopPoll]);

  const startSimulation = async () => {
    if (!strategyId.trim() || !marketId.trim() || !tokenId.trim()) {
      setError("strategy_id, market_id, and token_id are required.");
      return;
    }
    setError(null);
    setPollError(null);
    setLoading("sim");
    stopPoll();
    setSimResult(null);
    setRunAccept(null);
    try {
      const start = new Date(startLocal);
      const end = new Date(endLocal);
      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        throw new Error("Invalid simulation window.");
      }
      let config: Record<string, unknown> | undefined;
      const trimmed = configText.trim();
      if (trimmed) {
        config = JSON.parse(trimmed) as Record<string, unknown>;
      }
      const body: SimulationRunBody = {
        strategy_id: strategyId.trim(),
        market_id: marketId.trim(),
        token_id: tokenId.trim(),
        start: start.toISOString(),
        end: end.toISOString(),
        config,
      };
      const accepted = await postSimulationRun(body);
      setRunAccept(accepted);
      const rid = accepted.run_id;

      const pollOnce = async () => {
        try {
          const r = await fetchSimulationResult(rid);
          setSimResult(r);
          setPollError(null);
          const st =
            r &&
            typeof r === "object" &&
            "status" in r &&
            typeof (r as { status: unknown }).status === "string"
              ? (r as { status: string }).status
              : "";
          if (st === "completed" || st === "failed" || st === "error") {
            stopPoll();
          }
        } catch (e) {
          setPollError(parseError(e));
        }
      };
      void pollOnce();
      pollRef.current = setInterval(() => void pollOnce(), 2000);
    } catch (e) {
      if (e instanceof SyntaxError) {
        setError("config JSON is invalid.");
      } else {
        setError(parseError(e));
      }
    } finally {
      setLoading(null);
    }
  };

  const loadCompare = async () => {
    const ids = compareIds.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
    if (ids.length < 2) {
      setError("Enter at least two strategy_ids (comma or space separated).");
      return;
    }
    setError(null);
    setLoading("compare");
    try {
      setCompareOut(await fetchEvaluationCompare(ids));
    } catch (e) {
      setCompareOut(null);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  const loadEvalLatest = async () => {
    if (!evalStrategyId.trim()) {
      setError("Enter strategy_id for evaluation latest.");
      return;
    }
    setError(null);
    setLoading("ev-latest");
    try {
      setEvalLatest(await fetchEvaluationLatest(evalStrategyId.trim()));
    } catch (e) {
      setEvalLatest(null);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  const loadEvalRegimes = async () => {
    if (!evalStrategyId.trim()) {
      setError("Enter strategy_id for regime breakdown.");
      return;
    }
    setError(null);
    setLoading("ev-reg");
    try {
      setEvalRegimes(await fetchEvaluationRegimes(evalStrategyId.trim()));
    } catch (e) {
      setEvalRegimes([]);
      setError(parseError(e));
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <ExplorerPageHeader
        title="Simulation & evaluation"
        helpId="explorer-simulation"
        badges={[{ status: "stub", label: "Simulation/eval stubs until runner + DB wired" }]}
      />
      <p className="text-sm text-muted-foreground max-w-3xl">
        POST a run, then poll <code className="text-xs">GET /v1/simulation/{"{run_id}"}/result</code> every 2s until
        status settles. Evaluation helpers call <code className="text-xs">/v1/evaluation/*</code>.
      </p>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Simulation run</CardTitle>
          <CardDescription>Optional <code className="text-xs">config</code> must be valid JSON object.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">strategy_id</label>
              <Input value={strategyId} onChange={(e) => setStrategyId(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">market_id</label>
              <Input value={marketId} onChange={(e) => setMarketId(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">token_id</label>
              <Input value={tokenId} onChange={(e) => setTokenId(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">start</label>
              <Input type="datetime-local" value={startLocal} onChange={(e) => setStartLocal(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">end</label>
              <Input type="datetime-local" value={endLocal} onChange={(e) => setEndLocal(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">config (JSON object, optional)</label>
            <Textarea
              className="font-mono text-xs min-h-[80px]"
              placeholder='{"fee_bps": 2}'
              value={configText}
              onChange={(e) => setConfigText(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void startSimulation()} disabled={loading === "sim"}>
              Start run + poll
            </Button>
            <Button type="button" variant="outline" onClick={stopPoll}>
              Stop polling
            </Button>
          </div>
          {runAccept ? (
            <p className="text-sm text-muted-foreground">
              Accepted: <span className="font-mono">{runAccept.run_id}</span> — {runAccept.status}
            </p>
          ) : null}
          {pollError ? <p className="text-sm text-destructive">{pollError}</p> : null}
          {simResult != null ? <JsonBlock value={simResult} /> : loading === "sim" ? <Skeleton className="h-32 w-full" /> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Evaluation</CardTitle>
          <CardDescription>Compare strategies or inspect latest / regime slices.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">strategy_ids (compare)</label>
            <Input
              placeholder="id-a, id-b"
              value={compareIds}
              onChange={(e) => setCompareIds(e.target.value)}
            />
            <Button type="button" variant="secondary" onClick={() => void loadCompare()} disabled={loading === "compare"}>
              GET /evaluation/compare
            </Button>
            {compareOut != null ? <JsonBlock value={compareOut} /> : null}
          </div>
          <div className="space-y-2 border-t pt-4">
            <label className="text-xs text-muted-foreground">strategy_id</label>
            <Input value={evalStrategyId} onChange={(e) => setEvalStrategyId(e.target.value)} />
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={() => void loadEvalLatest()} disabled={loading === "ev-latest"}>
                Latest
              </Button>
              <Button type="button" variant="outline" onClick={() => void loadEvalRegimes()} disabled={loading === "ev-reg"}>
                Regimes
              </Button>
            </div>
            {evalLatest != null ? <JsonBlock value={evalLatest} /> : null}
            {evalRegimes.length > 0 ? <JsonBlock value={evalRegimes} /> : null}
          </div>
        </CardContent>
      </Card>

      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
