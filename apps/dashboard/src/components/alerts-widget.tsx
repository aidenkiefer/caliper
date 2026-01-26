"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, AlertCircle, Info, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Alert } from "@/lib/types";

interface AlertsWidgetProps {
  alerts: Alert[];
  onAcknowledge?: (alertId: string) => void;
}

const severityConfig = {
  INFO: {
    icon: Info,
    color: "text-blue-500",
    bg: "bg-blue-500/10",
  },
  WARNING: {
    icon: AlertTriangle,
    color: "text-warning",
    bg: "bg-warning/10",
  },
  ERROR: {
    icon: AlertCircle,
    color: "text-loss",
    bg: "bg-loss/10",
  },
  CRITICAL: {
    icon: AlertCircle,
    color: "text-loss",
    bg: "bg-loss/20",
  },
};

export function AlertsWidget({ alerts, onAcknowledge }: AlertsWidgetProps) {
  const formatTime = (date: string) => {
    return new Date(date).toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    });
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Recent Alerts</CardTitle>
        <Badge variant="secondary">
          {alerts.filter((a) => !a.acknowledged).length} unread
        </Badge>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {alerts.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No alerts
            </p>
          ) : (
            alerts.slice(0, 5).map((alert) => {
              const config = severityConfig[alert.severity];
              const Icon = config.icon;
              return (
                <div
                  key={alert.alert_id}
                  className={cn(
                    "flex items-start gap-3 rounded-lg p-3",
                    config.bg,
                    alert.acknowledged && "opacity-60"
                  )}
                >
                  <Icon className={cn("h-5 w-5 mt-0.5", config.color)} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{alert.message}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatTime(alert.created_at)}
                    </p>
                  </div>
                  {!alert.acknowledged && onAcknowledge && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => onAcknowledge(alert.alert_id)}
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
