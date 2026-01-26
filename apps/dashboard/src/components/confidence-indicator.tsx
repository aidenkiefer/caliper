"use client";

import { Badge } from '@/components/ui/badge';
import { TooltipWrapper } from '@/components/ui/tooltip-wrapper';

interface ConfidenceIndicatorProps {
  confidence: number;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function ConfidenceIndicator({ 
  confidence, 
  showLabel = true,
  size = 'md',
}: ConfidenceIndicatorProps) {
  // Determine confidence level
  let level: 'low' | 'normal' | 'high';
  let color: string;
  
  if (confidence < 0.65) {
    level = 'low';
    color = 'bg-red-500';
  } else if (confidence < 0.85) {
    level = 'normal';
    color = 'bg-yellow-500';
  } else {
    level = 'high';
    color = 'bg-emerald-500';
  }
  
  // Size classes
  const sizeClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4',
  };
  
  return (
    <div className="flex items-center gap-2">
      <TooltipWrapper term="Confidence">
        <div className="flex items-center gap-1">
          <div className="w-24 bg-muted rounded-full overflow-hidden">
            <div
              className={`${color} ${sizeClasses[size]} transition-all`}
              style={{ width: `${confidence * 100}%` }}
            />
          </div>
          {showLabel && (
            <span className="text-sm text-muted-foreground">
              {(confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>
      </TooltipWrapper>
      <Badge 
        variant="outline" 
        className={
          level === 'high' ? 'border-emerald-500 text-emerald-500' :
          level === 'normal' ? 'border-yellow-500 text-yellow-500' :
          'border-red-500 text-red-500'
        }
      >
        {level.toUpperCase()}
      </Badge>
    </div>
  );
}
