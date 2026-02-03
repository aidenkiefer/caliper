/**
 * Model Detail Page (Ticket 09-02)
 *
 * Comprehensive view of a single model with overview, training summary,
 * performance metrics, and lifecycle controls.
 */

'use client';

import { use } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import { modelsAPI, performanceAPI, driftAPI } from '@/lib/api/models';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Settings, AlertTriangle, Play, Pause, Archive } from 'lucide-react';

export default function ModelDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const { data: model, error: modelError } = useSWR(`model-${id}`, () => modelsAPI.get(id));
  const { data: performance } = useSWR(`perf-${id}`, () => performanceAPI.get(id, 30));
  const { data: health } = useSWR(`health-${id}`, () => driftAPI.health(id));

  if (modelError) return <div className="p-6">Error loading model</div>;
  if (!model) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6 space-y-6">
      {/* Header with Lifecycle Controls */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{model.name}</h1>
          <p className="text-muted-foreground mt-1">
            {model.type} · Trained {model.trainedDate}
          </p>
        </div>
        <div className="flex gap-2">
          {model.status === 'active' ? (
            <Button variant="outline" onClick={() => modelsAPI.updateStatus(id, 'paused')}>
              <Pause className="w-4 h-4 mr-2" />
              Pause
            </Button>
          ) : (
            <Button onClick={() => modelsAPI.updateStatus(id, 'active')}>
              <Play className="w-4 h-4 mr-2" />
              Activate
            </Button>
          )}
          <Button variant="outline" onClick={() => modelsAPI.updateStatus(id, 'retired')}>
            <Archive className="w-4 h-4 mr-2" />
            Retire
          </Button>
          <Link href={`/models/${id}/tune`}>
            <Button variant="outline">
              <Settings className="w-4 h-4 mr-2" />
              Tune
            </Button>
          </Link>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge>{model.status}</Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Health Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{model.healthScore}</div>
            <p className="text-xs text-muted-foreground">Out of 100</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Accuracy</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {model.accuracy ? `${(model.accuracy * 100).toFixed(1)}%` : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">30-day rolling</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Abstention Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(model.abstentionRate * 100).toFixed(0)}%
            </div>
            <p className="text-xs text-muted-foreground">Of predictions</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="drift">Drift & Health</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* Model Overview */}
          <Card>
            <CardHeader>
              <CardTitle>Model Architecture</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Type</dt>
                  <dd className="text-sm">{model.metadata.modelType}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Features</dt>
                  <dd className="text-sm">{model.metadata.features}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Training Samples</dt>
                  <dd className="text-sm">{model.metadata.samples}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Training Period</dt>
                  <dd className="text-sm">
                    {model.metadata.trainingPeriod[0]} to {model.metadata.trainingPeriod[1]}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* Training Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Training Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Model trained on {model.metadata.samples} samples from{' '}
                {model.metadata.trainingPeriod[0]} to {model.metadata.trainingPeriod[1]}.
                Using {model.metadata.features} features including technical indicators,
                returns, and volatility measures.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Performance Metrics</CardTitle>
              <CardDescription>30-day rolling window</CardDescription>
            </CardHeader>
            <CardContent>
              {performance ? (
                <dl className="grid grid-cols-2 gap-4">
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Total Predictions</dt>
                    <dd className="text-2xl font-bold">{performance.total_predictions}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Completed</dt>
                    <dd className="text-2xl font-bold">{performance.completed_predictions}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Accuracy</dt>
                    <dd className="text-2xl font-bold">
                      {performance.accuracy ? `${(performance.accuracy * 100).toFixed(1)}%` : 'N/A'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Avg Confidence</dt>
                    <dd className="text-2xl font-bold">
                      {performance.avg_confidence ? `${(performance.avg_confidence * 100).toFixed(0)}%` : 'N/A'}
                    </dd>
                  </div>
                </dl>
              ) : (
                <p>Loading performance data...</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="drift" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Health Score</CardTitle>
            </CardHeader>
            <CardContent>
              {health ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-4">
                    <div className="text-4xl font-bold">{health.health_score}</div>
                    <div className="flex-1">
                      <p className="text-sm text-muted-foreground">Overall Health</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="text-sm font-medium">Components</h4>
                    <dl className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <dt className="text-muted-foreground">Feature Drift</dt>
                        <dd className="font-medium">{health.components.feature_drift}</dd>
                      </div>
                      <div>
                        <dt className="text-muted-foreground">Confidence Drift</dt>
                        <dd className="font-medium">{health.components.confidence_drift}</dd>
                      </div>
                      <div>
                        <dt className="text-muted-foreground">Error Drift</dt>
                        <dd className="font-medium">{health.components.error_drift}</dd>
                      </div>
                      <div>
                        <dt className="text-muted-foreground">Staleness</dt>
                        <dd className="font-medium">{health.components.staleness}</dd>
                      </div>
                    </dl>
                  </div>

                  {health.alerts.length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-yellow-500" />
                        Alerts
                      </h4>
                      <ul className="space-y-1">
                        {health.alerts.map((alert, i) => (
                          <li key={i} className="text-sm text-yellow-600">{alert}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <p>Loading health data...</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Model Configuration</CardTitle>
              <CardDescription>Current threshold settings</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Configure model behavior thresholds. Changes require confirmation.
              </p>
              <Link href={`/models/${id}/tune`}>
                <Button>
                  <Settings className="w-4 h-4 mr-2" />
                  Adjust Thresholds
                </Button>
              </Link>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
