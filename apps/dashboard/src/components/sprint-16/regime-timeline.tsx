"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { RegimeTimelinePoint } from "@/lib/types/models";

const regimeClasses: Record<string, string> = {
  R1: "bg-emerald-500 text-white",
  R2: "bg-amber-500 text-white",
  R3: "bg-rose-500 text-white",
  R4: "bg-slate-500 text-white",
  R5: "bg-zinc-700 text-white",
};

export function RegimeTimeline({ points }: { points: RegimeTimelinePoint[] }) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Regime Timeline</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex h-12 overflow-hidden rounded-lg border">
          {points.map((point) => (
            <div
              key={point.timestamp}
              className={`flex-1 ${regimeClasses[point.regime] ?? "bg-muted"} flex items-center justify-center text-xs font-semibold text-white`}
              title={`${point.regime} • ${new Date(point.timestamp).toLocaleString()}`}
            >
              {point.regime}
            </div>
          ))}
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {points.map((point) => (
            <Card key={`${point.timestamp}-details`} className="border-dashed">
              <CardContent className="space-y-3 p-4">
                <div className="flex items-center justify-between">
                  <Badge className={regimeClasses[point.regime] ?? ""}>{point.regime}</Badge>
                  <span className="text-xs text-muted-foreground">
                    {new Date(point.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <div className="space-y-2">
                  {Object.entries(point.allocation_weights).map(([strategyId, weight]) => (
                    <div key={strategyId} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">{strategyId}</span>
                        <span className="font-medium">{(weight * 100).toFixed(0)}%</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${weight * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
