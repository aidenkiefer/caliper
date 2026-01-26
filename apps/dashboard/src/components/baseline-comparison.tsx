"use client";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface BaselineComparisonProps {
  strategyReturn: number;
  baselineReturns: {
    hold_cash: number;
    buy_and_hold: number;
    random?: number;
  };
  regretMetrics: {
    regret_vs_cash: number;
    regret_vs_buy_hold: number;
    regret_vs_random?: number;
  };
  outperforms: {
    cash: boolean;
    buy_and_hold: boolean;
    random?: boolean;
  };
}

export function BaselineComparison({
  strategyReturn,
  baselineReturns,
  regretMetrics,
  outperforms,
}: BaselineComparisonProps) {
  // Prepare chart data
  type ChartDataPoint = {
    name: string;
    return: number;
    fill: string;
  };
  
  const chartData: ChartDataPoint[] = [
    {
      name: 'Strategy',
      return: strategyReturn * 100,
      fill: '#3b82f6',
    },
    {
      name: 'Hold Cash',
      return: baselineReturns.hold_cash * 100,
      fill: '#6b7280',
    },
    {
      name: 'Buy & Hold',
      return: baselineReturns.buy_and_hold * 100,
      fill: '#6b7280',
    },
    ...(baselineReturns.random !== undefined ? [{
      name: 'Random',
      return: baselineReturns.random * 100,
      fill: '#6b7280',
    }] : []),
  ];
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Baseline Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Chart */}
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis label={{ value: 'Return (%)', angle: -90, position: 'insideLeft' }} />
                <Tooltip
                  formatter={(value: number) => `${value.toFixed(2)}%`}
                />
                <Bar 
                  dataKey="return" 
                  fill="#3b82f6"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          
          {/* Comparison Table */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Performance vs Baselines</h3>
            <div className="space-y-2">
              <ComparisonRow
                label="Hold Cash"
                strategyReturn={strategyReturn}
                baselineReturn={baselineReturns.hold_cash}
                regret={regretMetrics.regret_vs_cash}
                outperforms={outperforms.cash}
              />
              <ComparisonRow
                label="Buy & Hold"
                strategyReturn={strategyReturn}
                baselineReturn={baselineReturns.buy_and_hold}
                regret={regretMetrics.regret_vs_buy_hold}
                outperforms={outperforms.buy_and_hold}
              />
              {baselineReturns.random !== undefined && (
                <ComparisonRow
                  label="Random"
                  strategyReturn={strategyReturn}
                  baselineReturn={baselineReturns.random}
                  regret={regretMetrics.regret_vs_random!}
                  outperforms={outperforms.random!}
                />
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ComparisonRow({
  label,
  strategyReturn,
  baselineReturn,
  regret,
  outperforms,
}: {
  label: string;
  strategyReturn: number;
  baselineReturn: number;
  regret: number;
  outperforms: boolean;
}) {
  return (
    <div className="flex items-center justify-between p-3 border rounded-lg">
      <div className="flex items-center gap-2">
        <span className="font-medium">{label}</span>
        {outperforms ? (
          <Badge variant="default" className="bg-emerald-500">
            <TrendingUp className="h-3 w-3 mr-1" />
            Outperforms
          </Badge>
        ) : (
          <Badge variant="destructive">
            <TrendingDown className="h-3 w-3 mr-1" />
            Underperforms
          </Badge>
        )}
      </div>
      <div className="flex items-center gap-4 text-sm">
        <span className="text-muted-foreground">
          Strategy: {(strategyReturn * 100).toFixed(2)}%
        </span>
        <span className="text-muted-foreground">
          Baseline: {(baselineReturn * 100).toFixed(2)}%
        </span>
        <span className={regret > 0 ? 'text-emerald-500' : 'text-red-500'}>
          Regret: {(regret * 100).toFixed(2)}%
        </span>
      </div>
    </div>
  );
}
