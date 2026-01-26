"use client";

import { useState, useEffect } from "react";
import { Bell, Power, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";

interface HeaderProps {
  title: string;
  lastUpdated?: Date;
  alertCount?: number;
}

export function Header({ title, lastUpdated, alertCount = 0 }: HeaderProps) {
  const [stalenessSeconds, setStalenessSeconds] = useState(0);
  
  useEffect(() => {
    if (!lastUpdated) return;
    
    const updateStaleness = () => {
      const seconds = Math.floor((Date.now() - lastUpdated.getTime()) / 1000);
      setStalenessSeconds(seconds);
    };
    
    updateStaleness();
    const interval = setInterval(updateStaleness, 1000);
    return () => clearInterval(interval);
  }, [lastUpdated]);
  
  const isStale = stalenessSeconds > 30;
  
  const handleKillSwitch = () => {
    // TODO: Implement actual kill switch API call
    console.log("Kill switch activated");
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60 md:px-6">
      <div className="flex items-center gap-4 md:pl-0 pl-12">
        <h1 className="text-xl font-semibold">{title}</h1>
        {/* Data staleness indicator - per dashboard-spec.md risk mitigation */}
        {lastUpdated && (
          <span 
            className={cn(
              "text-xs font-mono",
              isStale ? "text-loss" : "text-muted-foreground"
            )}
            role="status"
            aria-live="polite"
          >
            {isStale && <AlertTriangle className="h-3 w-3 inline mr-1" aria-hidden="true" />}
            Updated: {stalenessSeconds}s ago
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Alerts */}
        <Button 
          variant="ghost" 
          size="icon" 
          className="relative"
          aria-label={`Notifications: ${alertCount} unread`}
        >
          <Bell className="h-5 w-5" />
          {alertCount > 0 && (
            <Badge className="absolute -right-1 -top-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs bg-loss">
              {alertCount}
            </Badge>
          )}
        </Button>

        {/* Kill Switch with confirmation dialog - per dashboard-spec.md risk mitigation */}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="destructive"
              size="sm"
              className="gap-2 bg-loss hover:bg-loss/90"
            >
              <Power className="h-4 w-4" />
              <span className="hidden sm:inline">Kill Switch</span>
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle className="flex items-center gap-2 text-loss">
                <AlertTriangle className="h-5 w-5" />
                Emergency Stop Confirmation
              </AlertDialogTitle>
              <AlertDialogDescription className="space-y-2">
                <p>This will immediately:</p>
                <ul className="list-disc list-inside text-sm space-y-1">
                  <li>Stop all active trading strategies</li>
                  <li>Cancel all pending orders</li>
                  <li>Close all open positions at market price</li>
                </ul>
                <p className="font-medium text-foreground">
                  Are you sure you want to activate the kill switch?
                </p>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction 
                onClick={handleKillSwitch}
                className="bg-loss hover:bg-loss/90"
              >
                Confirm Kill Switch
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </header>
  );
}
