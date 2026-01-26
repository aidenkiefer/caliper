"use client";

import { useHealth } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Database,
  Radio,
  Server,
  Zap,
  CheckCircle,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

const statusConfig = {
  healthy: { icon: CheckCircle, color: "text-profit", bg: "bg-profit/10" },
  degraded: { icon: AlertTriangle, color: "text-warning", bg: "bg-warning/10" },
  unhealthy: { icon: XCircle, color: "text-loss", bg: "bg-loss/10" },
};

const serviceIcons: Record<string, typeof Database> = {
  database: Database,
  data_feed: Radio,
  broker_connection: Server,
  redis: Zap,
};

export default function HealthPage() {
  const { health } = useHealth();

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const overallStatus = statusConfig[health.status];
  const OverallIcon = overallStatus.icon;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold">System Health</h2>
          <p className="text-muted-foreground">
            Infrastructure and service status
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={cn("text-sm", overallStatus.bg, overallStatus.color)}>
            <OverallIcon className="h-4 w-4 mr-1" />
            System {health.status}
          </Badge>
          <span className="text-sm text-muted-foreground">
            Updated: {formatTime(health.timestamp)}
          </span>
        </div>
      </div>

      {/* Service Status Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {Object.entries(health.services).map(([serviceName, service]) => {
          const status = statusConfig[service.status];
          const StatusIcon = status.icon;
          const ServiceIcon = serviceIcons[serviceName] || Server;

          return (
            <Card key={serviceName} className={cn(status.bg)}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <ServiceIcon className="h-5 w-5" />
                  <span className="capitalize">
                    {serviceName.replace(/_/g, " ")}
                  </span>
                </CardTitle>
                <StatusIcon className={cn("h-5 w-5", status.color)} />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Status</span>
                    <Badge
                      variant="outline"
                      className={cn("capitalize", status.color)}
                    >
                      {service.status}
                    </Badge>
                  </div>

                  {service.latency_ms !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Latency
                      </span>
                      <span className="font-mono text-sm">
                        {service.latency_ms}ms
                      </span>
                    </div>
                  )}

                  {service.staleness_seconds !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Data Staleness
                      </span>
                      <span
                        className={cn(
                          "font-mono text-sm",
                          service.staleness_seconds > 30 && "text-warning"
                        )}
                      >
                        {service.staleness_seconds}s
                      </span>
                    </div>
                  )}

                  {service.broker && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Broker
                      </span>
                      <span className="font-mono text-sm capitalize">
                        {service.broker}
                      </span>
                    </div>
                  )}

                  {service.mode && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Mode</span>
                      <Badge variant="outline" className="text-xs">
                        {service.mode}
                      </Badge>
                    </div>
                  )}

                  {service.last_update && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Last Update
                      </span>
                      <span className="font-mono text-xs">
                        {formatTime(service.last_update)}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* API Rate Limits */}
      <Card>
        <CardHeader>
          <CardTitle>API Rate Limits</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Alpaca API</span>
                <span className="font-mono">450/1000 requests</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-profit transition-all"
                  style={{ width: "45%" }}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Dashboard API</span>
                <span className="font-mono">75/100 requests/min</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-warning transition-all"
                  style={{ width: "75%" }}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Backtest Queue</span>
                <span className="font-mono">2/5 concurrent</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-profit transition-all"
                  style={{ width: "40%" }}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
