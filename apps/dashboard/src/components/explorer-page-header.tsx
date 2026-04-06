import Link from "next/link";

import { HelpHint } from "@/components/help-hint";
import { StatusBadge } from "@/components/status-badge";
import type { CapabilityStatus } from "@/components/status-badge";
import { Button } from "@/components/ui/button";

export function ExplorerPageHeader({
  title,
  helpId,
  badges,
  backHref = "/platform",
}: {
  title: string;
  helpId: string;
  badges?: { status: CapabilityStatus; label?: string }[];
  backHref?: string;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight flex flex-wrap items-center gap-2">
          {title}
          <HelpHint helpId={helpId} label={title} />
        </h2>
        {badges?.length ? (
          <div className="mt-2 flex flex-wrap gap-2">
            {badges.map((b, i) => (
              <StatusBadge
                key={i}
                status={b.status}
                aria-label={b.label ?? b.status}
              />
            ))}
          </div>
        ) : null}
      </div>
      <Button variant="outline" size="sm" asChild>
        <Link href={backHref}>Back to platform</Link>
      </Button>
    </div>
  );
}
