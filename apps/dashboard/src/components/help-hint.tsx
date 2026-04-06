"use client";

import * as React from "react";
import { CircleHelp } from "lucide-react";

import { useMediaQuery } from "@/hooks/use-media-query";
import { HELP_COPY } from "@/lib/help/copy";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface HelpHintProps {
  helpId: keyof typeof HELP_COPY | (string & {});
  className?: string;
  /** Accessible label fragment, e.g. "Total P&L" */
  label?: string;
}

export function HelpHint({ helpId, className, label }: HelpHintProps) {
  const isCoarsePointer = useMediaQuery("(max-width: 768px)");
  const copy = HELP_COPY[helpId as string];
  const [sheetOpen, setSheetOpen] = React.useState(false);

  if (!copy) {
    return null;
  }

  const ariaLabel = label
    ? `Explain ${label}`
    : `Explain: ${copy.title}`;

  if (isCoarsePointer) {
    return (
      <>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={cn("h-7 w-7 shrink-0 text-muted-foreground", className)}
          aria-label={ariaLabel}
          aria-expanded={sheetOpen}
          onClick={(e) => {
            e.stopPropagation();
            setSheetOpen(true);
          }}
        >
          <CircleHelp className="h-4 w-4" aria-hidden />
        </Button>
        {sheetOpen ? (
          <>
            <button
              type="button"
              className="fixed inset-0 z-50 bg-black/60"
              aria-label="Close help"
              onClick={() => setSheetOpen(false)}
            />
            <div
              className="fixed bottom-0 left-0 right-0 z-50 max-h-[min(70vh,28rem)] overflow-y-auto rounded-t-xl border border-border bg-background p-4 shadow-lg animate-in slide-in-from-bottom-4 duration-200"
              role="dialog"
              aria-modal="true"
              aria-labelledby={`help-sheet-title-${helpId}`}
            >
              <div className="mx-auto max-w-lg space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <h2
                    id={`help-sheet-title-${helpId}`}
                    className="text-base font-semibold"
                  >
                    {copy.title}
                  </h2>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => setSheetOpen(false)}
                  >
                    Close
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {copy.body}
                </p>
                {copy.readMoreHref ? (
                  <a
                    href={copy.readMoreHref}
                    className="inline-block text-sm text-primary underline-offset-4 hover:underline"
                    onClick={() => setSheetOpen(false)}
                  >
                    Read more
                  </a>
                ) : null}
              </div>
            </div>
          </>
        ) : null}
      </>
    );
  }

  return (
    <Tooltip delayDuration={200}>
      <TooltipTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            className
          )}
          aria-label={ariaLabel}
          onClick={(e) => e.stopPropagation()}
        >
          <CircleHelp className="h-4 w-4" aria-hidden />
        </button>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        className="max-w-xs border bg-popover px-3 py-2 text-popover-foreground shadow-md"
      >
        <p className="mb-1 font-medium">{copy.title}</p>
        <p className="text-xs text-muted-foreground leading-relaxed">
          {copy.body}
        </p>
        {copy.readMoreHref ? (
          <a
            href={copy.readMoreHref}
            className="mt-2 inline-block text-xs text-primary underline-offset-4 hover:underline"
          >
            Read more
          </a>
        ) : null}
      </TooltipContent>
    </Tooltip>
  );
}
