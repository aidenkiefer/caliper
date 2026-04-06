import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export type CapabilityStatus = "live" | "mock" | "stub" | "cli" | "docs";

const styles: Record<CapabilityStatus, string> = {
  live: "border-emerald-500/50 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  mock: "border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  stub: "border-orange-500/50 bg-orange-500/10 text-orange-700 dark:text-orange-400",
  cli: "border-violet-500/50 bg-violet-500/10 text-violet-700 dark:text-violet-300",
  docs: "border-muted-foreground/40 bg-muted text-muted-foreground",
};

const labels: Record<CapabilityStatus, string> = {
  live: "Live",
  mock: "Mock",
  stub: "Stub",
  cli: "CLI",
  docs: "Docs",
};

export function StatusBadge({
  status,
  className,
  ...props
}: {
  status: CapabilityStatus;
  className?: string;
} & HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      role="status"
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
        styles[status],
        className
      )}
      {...props}
    >
      {labels[status]}
    </span>
  );
}
