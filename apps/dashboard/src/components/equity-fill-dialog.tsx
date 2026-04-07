"use client";

import { useMemo, useState } from "react";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createEquityFill } from "@/lib/api";

export function EquityFillDialog(props: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategyId?: string;
  strategyName?: string;
  onSuccess?: () => void;
}) {
  const strategyId = props.strategyId ?? "";
  const strategyLabel = useMemo(() => {
    if (props.strategyName) return props.strategyName;
    if (strategyId) return strategyId;
    return "strategy";
  }, [props.strategyName, strategyId]);

  const [symbol, setSymbol] = useState("SPY");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("1");
  const [price, setPrice] = useState("100");
  const [feesUsd, setFeesUsd] = useState("0");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!strategyId) return;
    const q = quantity.trim();
    const p = price.trim();
    const f = feesUsd.trim();
    if (!symbol.trim()) {
      setError("Symbol is required.");
      return;
    }
    if (!q || Number.isNaN(Number(q)) || Number(q) <= 0) {
      setError("Enter a valid quantity.");
      return;
    }
    if (!p || Number.isNaN(Number(p)) || Number(p) <= 0) {
      setError("Enter a valid price.");
      return;
    }
    if (!f || Number.isNaN(Number(f)) || Number(f) < 0) {
      setError("Enter a valid fees amount.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await createEquityFill({
        strategy_id: strategyId,
        symbol: symbol.trim().toUpperCase(),
        side,
        quantity: q,
        price: p,
        fees_usd: f,
      });
      props.onSuccess?.();
      props.onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to record fill.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AlertDialog open={props.open} onOpenChange={props.onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Record equities paper fill</AlertDialogTitle>
          <AlertDialogDescription>
            Append a fill to <span className="font-medium">{strategyLabel}</span>. This is a Phase 1
            tool for wiring honest paper MTM from fills.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">Symbol</label>
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="AAPL"
              disabled={!strategyId || isSubmitting}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Side</label>
            <Select value={side} onValueChange={(v) => setSide(v as "BUY" | "SELL")}>
              <SelectTrigger disabled={!strategyId || isSubmitting}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BUY">BUY</SelectItem>
                <SelectItem value="SELL">SELL</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Quantity</label>
            <Input
              inputMode="decimal"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="1"
              disabled={!strategyId || isSubmitting}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Price</label>
            <Input
              inputMode="decimal"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="100"
              disabled={!strategyId || isSubmitting}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Fees (USD)</label>
            <Input
              inputMode="decimal"
              value={feesUsd}
              onChange={(e) => setFeesUsd(e.target.value)}
              placeholder="0"
              disabled={!strategyId || isSubmitting}
            />
          </div>
        </div>

        <div className="pt-1">
          {error && <p className="text-sm text-destructive">{error}</p>}
          {!strategyId && (
            <p className="text-xs text-muted-foreground">Select a strategy to record a fill.</p>
          )}
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={isSubmitting}>Cancel</AlertDialogCancel>
          <Button onClick={submit} disabled={!strategyId || isSubmitting}>
            {isSubmitting ? "Recording..." : "Record fill"}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

