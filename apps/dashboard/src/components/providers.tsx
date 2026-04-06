"use client";

import { SWRConfig } from "swr";

import { TooltipProvider } from "@/components/ui/tooltip";

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <SWRConfig
      value={{
        revalidateOnFocus: false,
        revalidateIfStale: true,
        dedupingInterval: 2000,
      }}
    >
      <TooltipProvider delayDuration={200} skipDelayDuration={0}>
        {children}
      </TooltipProvider>
    </SWRConfig>
  );
}
