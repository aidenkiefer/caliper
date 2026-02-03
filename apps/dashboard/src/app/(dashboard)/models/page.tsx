/**
 * Model Registry Page (Ticket 09-01)
 *
 * List view of all models with sorting, filtering, and quick actions.
 */

'use client';

import { useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import { modelsAPI } from '@/lib/api/models';
import type { ModelStatus, ModelType } from '@/lib/types/models';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Activity, Play, Pause, Eye } from 'lucide-react';

type SortField = 'name' | 'status' | 'trainedDate' | 'healthScore' | 'accuracy';
type SortDirection = 'asc' | 'desc';

export default function ModelsPage() {
  const { data: models, error, isLoading } = useSWR('models', modelsAPI.list);

  const [sortField] = useState<SortField>('healthScore');
  const [sortDirection] = useState<SortDirection>('desc');
  const [statusFilter, setStatusFilter] = useState<ModelStatus | 'all'>('all');
  const [typeFilter, setTypeFilter] = useState<ModelType | 'all'>('all');

  const filteredAndSortedModels = models
    ?.filter((m) => statusFilter === 'all' || m.status === statusFilter)
    ?.filter((m) => typeFilter === 'all' || m.type === typeFilter)
    ?.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      if (aVal === null || bVal === null) return 0;
      const compare = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortDirection === 'asc' ? compare : -compare;
    });

  if (isLoading) return <div className="p-6">Loading models...</div>;
  if (error) return <div className="p-6">Error loading models</div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Model Registry</h1>
        <p className="text-muted-foreground mt-1">
          View and manage all ML models
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ModelStatus | 'all')}
              className="px-3 py-2 border rounded"
            >
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="candidate">Candidate</option>
              <option value="paused">Paused</option>
              <option value="retired">Retired</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Type</label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as ModelType | 'all')}
              className="px-3 py-2 border rounded"
            >
              <option value="all">All</option>
              <option value="logistic">Logistic</option>
              <option value="tree">Tree</option>
              <option value="ensemble">Ensemble</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Models Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Trained</TableHead>
                <TableHead>Health</TableHead>
                <TableHead>Accuracy</TableHead>
                <TableHead>Allocation</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAndSortedModels?.map((model) => (
                <TableRow key={model.id}>
                  <TableCell className="font-medium">{model.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{model.type}</Badge>
                  </TableCell>
                  <TableCell>
                    <ModelStatusBadge status={model.status} />
                  </TableCell>
                  <TableCell>{model.trainedDate}</TableCell>
                  <TableCell>
                    <HealthScoreBadge score={model.healthScore} />
                  </TableCell>
                  <TableCell>
                    {model.accuracy ? `${(model.accuracy * 100).toFixed(1)}%` : 'N/A'}
                  </TableCell>
                  <TableCell>
                    {(model.allocationWeight * 100).toFixed(0)}%
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Link href={`/models/${model.id}`}>
                        <Button size="sm" variant="outline">
                          <Eye className="w-4 h-4" />
                        </Button>
                      </Link>
                      {model.status === 'active' ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => modelsAPI.updateStatus(model.id, 'paused')}
                        >
                          <Pause className="w-4 h-4" />
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => modelsAPI.updateStatus(model.id, 'active')}
                        >
                          <Play className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function ModelStatusBadge({ status }: { status: ModelStatus }) {
  const variants: Record<ModelStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
    active: 'default',
    candidate: 'secondary',
    paused: 'outline',
    retired: 'destructive'
  };

  return <Badge variant={variants[status]}>{status}</Badge>;
}

function HealthScoreBadge({ score }: { score: number }) {
  const color = score >= 80 ? 'text-green-500' : score >= 60 ? 'text-yellow-500' : 'text-red-500';
  return (
    <div className={`flex items-center gap-2 ${color}`}>
      <Activity className="w-4 h-4" />
      <span className="font-medium">{score}</span>
    </div>
  );
}
