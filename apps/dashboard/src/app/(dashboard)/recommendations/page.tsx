"use client";

import useSWR from "swr";
import { useState } from "react";
import { ApprovalQueue } from '@/components/approval-queue';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';
import { approveRecommendation, listPendingRecommendations, rejectRecommendation } from "@/lib/api/recommendations";

export default function RecommendationsPage() {
  const [isLoading, setIsLoading] = useState(false);

  const {
    data: recommendations = [],
    error,
    mutate,
  } = useSWR("recommendations", () => listPendingRecommendations(), {
    refreshInterval: 10_000,
  });

  const handleApprove = async (id: string) => {
    setIsLoading(true);
    try {
      await approveRecommendation(id, { user_id: "dashboard_user" });
      await mutate();
    } finally {
      setIsLoading(false);
    }
  };

  const handleReject = async (id: string) => {
    setIsLoading(true);
    try {
      await rejectRecommendation(id, { user_id: "dashboard_user", reason: "Rejected in dashboard" });
      await mutate();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Recommendation Queue</h1>
          <p className="text-muted-foreground mt-2">
            Review and approve model recommendations before execution
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => mutate()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <Card className="border-loss/50">
          <CardHeader>
            <CardTitle className="text-loss">Backend unavailable</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Unable to load the HITL recommendation queue from the API.
            </p>
          </CardContent>
        </Card>
      )}

      <ApprovalQueue
        recommendations={recommendations}
        onApprove={handleApprove}
        onReject={handleReject}
        isLoading={isLoading}
      />

      <Card>
        <CardHeader>
          <CardTitle>HITL Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <p className="text-sm text-muted-foreground">Total Recommendations</p>
              <p className="text-2xl font-bold">—</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Agreement Rate</p>
              <p className="text-2xl font-bold">—</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Pending</p>
              <p className="text-2xl font-bold">{recommendations.length}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
