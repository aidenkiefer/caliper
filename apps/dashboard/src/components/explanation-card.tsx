"use client";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TooltipWrapper } from '@/components/ui/tooltip-wrapper';
import { ArrowUp, ArrowDown } from 'lucide-react';

interface FeatureContribution {
  feature_name: string;
  value: number;
  contribution: number;
  direction: 'positive' | 'negative';
}

interface ExplanationCardProps {
  tradeId: string;
  signal: 'BUY' | 'SELL' | 'ABSTAIN';
  confidence: number;
  topFeatures: FeatureContribution[];
  baseValue?: number;
}

export function ExplanationCard({ 
  tradeId: _tradeId, 
  signal, 
  confidence, 
  topFeatures,
  baseValue,
}: ExplanationCardProps) {
  const signalColor = {
    BUY: 'bg-emerald-500',
    SELL: 'bg-red-500',
    ABSTAIN: 'bg-yellow-500'
  };
  
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">
          <TooltipWrapper term="SHAP">Trade Explanation</TooltipWrapper>
        </CardTitle>
        <div className="flex items-center gap-2">
          <Badge className={signalColor[signal]}>{signal}</Badge>
          <TooltipWrapper term="Confidence">
            <span className="text-sm text-muted-foreground">
              {(confidence * 100).toFixed(1)}% confident
            </span>
          </TooltipWrapper>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          Key factors influencing this recommendation:
        </p>
        <div className="space-y-3">
          {topFeatures.map((feature, idx) => (
            <FeatureRow key={idx} feature={feature} />
          ))}
        </div>
        {baseValue !== undefined && (
          <p className="text-xs text-muted-foreground mt-4">
            Base value: {baseValue.toFixed(4)}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function FeatureRow({ feature }: { feature: FeatureContribution }) {
  const isPositive = feature.direction === 'positive';
  const contributionAbs = Math.abs(feature.contribution);
  
  return (
    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
      <span className="text-sm font-medium">{feature.feature_name}</span>
      <div className="flex items-center gap-3">
        <span className="text-xs text-muted-foreground">
          Value: {feature.value.toFixed(2)}
        </span>
        <div className={`flex items-center gap-1 text-sm font-medium ${
          isPositive ? 'text-emerald-500' : 'text-red-500'
        }`}>
          {isPositive ? (
            <ArrowUp className="h-4 w-4" />
          ) : (
            <ArrowDown className="h-4 w-4" />
          )}
          <span>{contributionAbs.toFixed(3)}</span>
        </div>
      </div>
    </div>
  );
}
