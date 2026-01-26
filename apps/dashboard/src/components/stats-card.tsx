import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipWrapper } from "@/components/ui/tooltip-wrapper";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatsCardProps {
  title: string;
  value: string;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon?: LucideIcon;
  className?: string;
  /** Show pulsing indicator for live data */
  isLive?: boolean;
}

export function StatsCard({
  title,
  value,
  change,
  changeType = "neutral",
  icon: Icon,
  className,
  isLive,
}: StatsCardProps) {
  return (
    <Card className={cn("hover:bg-card-hover transition-colors", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <TooltipWrapper term={title} showIcon={false}>
            {title}
          </TooltipWrapper>
          {isLive && (
            <span className="h-2 w-2 rounded-full bg-profit pulse-live" aria-label="Live data" />
          )}
        </CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold font-tabular">{value}</div>
        {change && (
          <p
            className={cn(
              "text-xs mt-1",
              changeType === "positive" && "text-profit",
              changeType === "negative" && "text-loss",
              changeType === "neutral" && "text-muted-foreground"
            )}
          >
            {change}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
