'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getJobs, retryJob, cancelJob } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import Link from 'next/link';
import { RefreshCw, X, ChevronRight } from 'lucide-react';

export default function PublishingPage() {
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => getJobs().then((r) => r.data),
    refetchInterval: 10_000,
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => retryJob(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => cancelJob(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  });

  const jobs = data ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Publishing Jobs</h1>

      <div className="card overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-400">Loading jobs...</p>
        ) : error ? (
          <p className="p-6 text-sm text-red-500">Failed to load jobs.</p>
        ) : jobs.length === 0 ? (
          <p className="p-6 text-sm text-gray-400">No publishing jobs yet.</p>
        ) : (
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="table-header">ID</th>
                <th className="table-header">Status</th>
                <th className="table-header">Retries</th>
                <th className="table-header">Scheduled</th>
                <th className="table-header">Published</th>
                <th className="table-header">Failure</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {jobs.map((job: any) => (
                <tr key={job.id} className="hover:bg-gray-50">
                  <td className="table-cell font-mono text-xs text-gray-600">
                    {job.id.slice(0, 8)}…
                  </td>
                  <td className="table-cell">
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="table-cell text-center">
                    <span
                      className={
                        job.retry_count > 0
                          ? 'text-orange-600 font-medium'
                          : 'text-gray-400'
                      }
                    >
                      {job.retry_count}
                    </span>
                  </td>
                  <td className="table-cell text-gray-500 text-xs">
                    {job.scheduled_at
                      ? new Date(job.scheduled_at).toLocaleString()
                      : '—'}
                  </td>
                  <td className="table-cell text-gray-500 text-xs">
                    {job.published_at
                      ? new Date(job.published_at).toLocaleString()
                      : '—'}
                  </td>
                  <td className="table-cell text-red-500 text-xs max-w-xs truncate">
                    {job.failure_reason ?? '—'}
                  </td>
                  <td className="table-cell">
                    <div className="flex items-center gap-2">
                      {['failed', 'cancelled'].includes(job.status) && (
                        <button
                          onClick={() => retryMutation.mutate(job.id)}
                          disabled={retryMutation.isPending}
                          className="inline-flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700"
                          title="Retry"
                        >
                          <RefreshCw size={12} /> Retry
                        </button>
                      )}
                      {['queued', 'failed'].includes(job.status) && (
                        <button
                          onClick={() => cancelMutation.mutate(job.id)}
                          disabled={cancelMutation.isPending}
                          className="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-600"
                          title="Cancel"
                        >
                          <X size={12} /> Cancel
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
