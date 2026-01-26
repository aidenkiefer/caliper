"use client";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Check, X, Clock } from 'lucide-react';
import { TooltipWrapper } from '@/components/ui/tooltip-wrapper';

interface Recommendation {
  recommendation_id: string;
  strategy_id: string;
  signal: 'BUY' | 'SELL';
  symbol: string;
  confidence: number;
  uncertainty: number;
  timestamp: string;
  explanation_id?: string;
}

interface ApprovalQueueProps {
  recommendations: Recommendation[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  isLoading?: boolean;
}

export function ApprovalQueue({ 
  recommendations, 
  onApprove, 
  onReject,
  isLoading = false,
}: ApprovalQueueProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Pending Approvals
        </CardTitle>
        <Badge variant="outline">{recommendations.length} pending</Badge>
      </CardHeader>
      <CardContent>
        {recommendations.length === 0 ? (
          <p className="text-muted-foreground text-center py-4">
            No pending recommendations
          </p>
        ) : (
          <div className="space-y-4">
            {recommendations.map(rec => (
              <RecommendationCard
                key={rec.recommendation_id}
                recommendation={rec}
                onApprove={() => onApprove(rec.recommendation_id)}
                onReject={() => onReject(rec.recommendation_id)}
                isLoading={isLoading}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RecommendationCard({
  recommendation,
  onApprove,
  onReject,
  isLoading,
}: {
  recommendation: Recommendation;
  onApprove: () => void;
  onReject: () => void;
  isLoading: boolean;
}) {
  return (
    <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <Badge variant={recommendation.signal === 'BUY' ? 'default' : 'destructive'}>
            {recommendation.signal}
          </Badge>
          <span className="font-medium">{recommendation.symbol}</span>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>{recommendation.strategy_id}</span>
          <TooltipWrapper term="Confidence">
            <span>{(recommendation.confidence * 100).toFixed(0)}% confident</span>
          </TooltipWrapper>
          {recommendation.explanation_id && (
            <span className="text-xs text-primary hover:underline cursor-pointer">
              View explanation
            </span>
          )}
        </div>
      </div>
      <div className="flex gap-2">
        <Button 
          size="sm" 
          variant="outline"
          onClick={onReject}
          disabled={isLoading}
        >
          <X className="h-4 w-4" />
        </Button>
        <Button 
          size="sm"
          onClick={onApprove}
          disabled={isLoading}
        >
          <Check className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
