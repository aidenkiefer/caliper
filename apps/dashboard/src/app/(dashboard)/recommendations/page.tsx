"use client";

import { useState } from 'react';
import { ApprovalQueue } from '@/components/approval-queue';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';

// Mock data - in production, fetch from API
const mockRecommendations = [
  {
    recommendation_id: 'rec-1',
    strategy_id: 'strategy-1',
    signal: 'BUY' as const,
    symbol: 'AAPL',
    confidence: 0.78,
    uncertainty: 0.15,
    timestamp: new Date().toISOString(),
    explanation_id: 'exp-1',
  },
  {
    recommendation_id: 'rec-2',
    strategy_id: 'strategy-2',
    signal: 'SELL' as const,
    symbol: 'TSLA',
    confidence: 0.65,
    uncertainty: 0.22,
    timestamp: new Date().toISOString(),
  },
];

export default function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState(mockRecommendations);
  const [isLoading, setIsLoading] = useState(false);

  const handleApprove = async (id: string) => {
    setIsLoading(true);
    // In production, call API: POST /v1/recommendations/{id}/approve
    await new Promise(resolve => setTimeout(resolve, 500));
    setRecommendations(recs => recs.filter(r => r.recommendation_id !== id));
    setIsLoading(false);
  };

  const handleReject = async (id: string) => {
    setIsLoading(true);
    // In production, call API: POST /v1/recommendations/{id}/reject
    await new Promise(resolve => setTimeout(resolve, 500));
    setRecommendations(recs => recs.filter(r => r.recommendation_id !== id));
    setIsLoading(false);
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
        <Button variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

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
              <p className="text-2xl font-bold">42</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Agreement Rate</p>
              <p className="text-2xl font-bold">85%</p>
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
