"use client";

import { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";
import Link from "next/link";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function StrategyDetailError({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error("Strategy detail error:", error);
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="max-w-md w-full">
        <CardHeader className="text-center">
          <div className="mx-auto w-12 h-12 rounded-full bg-loss/10 flex items-center justify-center mb-4">
            <AlertCircle className="h-6 w-6 text-loss" />
          </div>
          <CardTitle className="text-xl">Strategy not found</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-center text-muted-foreground">
            Unable to load this strategy. It may have been deleted or you may not
            have access to it.
          </p>

          {error.message && (
            <div className="p-3 rounded-lg bg-muted">
              <p className="text-sm font-mono text-muted-foreground break-all">
                {error.message}
              </p>
            </div>
          )}

          <div className="flex gap-2 justify-center">
            <Button onClick={reset} variant="default" className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Retry
            </Button>
            <Link href="/strategies">
              <Button variant="outline" className="gap-2">
                <ArrowLeft className="h-4 w-4" />
                Back to Strategies
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
