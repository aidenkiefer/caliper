"use client";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { HelpCircle } from "lucide-react";
import { glossaryTerms } from "@/lib/glossary";
import Link from "next/link";

interface TooltipWrapperProps {
  term: string;
  children?: React.ReactNode;
  showIcon?: boolean;
}

export function TooltipWrapper({ term, children, showIcon = true }: TooltipWrapperProps) {
  const glossaryEntry = glossaryTerms.find(
    t => t.term.toLowerCase() === term.toLowerCase()
  );
  
  if (!glossaryEntry) {
    return <>{children || term}</>;
  }
  
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center gap-1 cursor-help">
            {children || term}
            {showIcon && (
              <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="text-sm">{glossaryEntry.definition}</p>
          {glossaryEntry.example && (
            <p className="text-xs text-muted-foreground mt-1">
              Example: {glossaryEntry.example}
            </p>
          )}
          <Link 
            href="/help" 
            className="text-xs text-primary hover:underline mt-2 block"
          >
            Learn more →
          </Link>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
