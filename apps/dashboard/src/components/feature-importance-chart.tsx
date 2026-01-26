"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface FeatureContribution {
  feature_name: string;
  value: number;
  contribution: number;
  direction: 'positive' | 'negative';
}

interface FeatureImportanceChartProps {
  features: FeatureContribution[];
  maxFeatures?: number;
}

export function FeatureImportanceChart({ 
  features, 
  maxFeatures = 10 
}: FeatureImportanceChartProps) {
  // Sort by absolute contribution and take top N
  const sortedFeatures = [...features]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, maxFeatures);
  
  // Prepare data for chart
  type ChartDataPoint = {
    name: string;
    contribution: number;
    absContribution: number;
    direction: 'positive' | 'negative';
    fill: string;
  };
  
  const chartData: ChartDataPoint[] = sortedFeatures.map(f => ({
    name: f.feature_name,
    contribution: f.contribution,
    absContribution: Math.abs(f.contribution),
    direction: f.direction,
    fill: f.direction === 'positive' ? '#22c55e' : '#ef4444',
  }));
  
  return (
    <div className="w-full h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis 
            dataKey="name" 
            type="category" 
            width={90}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-background border rounded-lg p-3 shadow-lg">
                    <p className="font-medium">{data.name}</p>
                    <p className="text-sm text-muted-foreground">
                      Contribution: {data.contribution.toFixed(4)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Direction: {data.direction}
                    </p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar 
            dataKey="contribution" 
            radius={[0, 4, 4, 0]}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            cell={(props: any) => {
              const fillColor = props.payload?.fill || '#8884d8';
              return <rect {...props} fill={fillColor} />;
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
