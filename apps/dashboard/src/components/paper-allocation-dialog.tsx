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
import { Textarea } from "@/components/ui/textarea";
import { createPaperAllocation } from "@/lib/api";

export function PaperAllocationDialog(props: {
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

  const [amountUsd, setAmountUsd] = useState("100");
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!strategyId) return;
    const amount = amountUsd.trim();
    if (!amount || Number.isNaN(Number(amount)) || Number(amount) <= 0) {
      setError("Enter a valid allocation amount (USD).");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await createPaperAllocation({
        strategy_id: strategyId,
        amount_usd: amount,
        note: note.trim() ? note.trim() : undefined,
      });
      props.onSuccess?.();
      props.onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to allocate capital.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AlertDialog open={props.open} onOpenChange={props.onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Allocate paper capital</AlertDialogTitle>
          <AlertDialogDescription>
            Add paper USD to <span className="font-medium">{strategyLabel}</span>. Allocations are additive
            contributions (no weekly reset).
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-3">
          <div className="space-y-2">
            <label className="text-sm font-medium">Amount (USD)</label>
            <Input
              inputMode="decimal"
              value={amountUsd}
              onChange={(e) => setAmountUsd(e.target.value)}
              placeholder="100"
              disabled={!strategyId || isSubmitting}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Note (optional)</label>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Weekly funding, manual top-up, etc."
              disabled={!strategyId || isSubmitting}
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          {!strategyId && (
            <p className="text-xs text-muted-foreground">Select a strategy to allocate capital.</p>
          )}
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={isSubmitting}>Cancel</AlertDialogCancel>
          <Button onClick={submit} disabled={!strategyId || isSubmitting}>
            {isSubmitting ? "Allocating..." : "Allocate"}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

