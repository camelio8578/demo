'use client';

import { useQuery } from '@tanstack/react-query';
import { getAnalyticsSummary } from '@/lib/api';

export default function AnalyticsPage() {
  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: () => getAnalyticsSummary().then((r) => r.data),
    refetchInterval: 60_000,
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h1>

      {isLoading ? (
        <p className="text-sm text-gray-400">Loading analytics...</p>
      ) : error ? (
        <p className="text-sm text-red-500">Failed to load analytics.</p>
      ) : summary ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div className="card p-5">
              <p className="text-xs text-gray-500 mb-1">Total Snapshots</p>
              <p className="text-2xl font-bold">{summary.total_snapshots}</p>
            </div>
            <div className="card p-5">
              <p className="text-xs text-gray-500 mb-1">Published Jobs</p>
              <p className="text-2xl font-bold">{summary.total_published_jobs}</p>
            </div>
            <div className="card p-5">
              <p className="text-xs text-gray-500 mb-1">Generated At</p>
              <p className="text-sm font-medium text-gray-700">
                {new Date(summary.generated_at).toLocaleString()}
              </p>
            </div>
          </div>

          {Object.keys(summary.platform_breakdown ?? {}).length > 0 && (
            <div className="card p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-4">
                Platform Breakdown (Total Views)
              </h2>
              <dl className="space-y-2">
                {Object.entries(summary.platform_breakdown).map(
                  ([platform, views]) => (
                    <div
                      key={platform}
                      className="flex justify-between text-sm"
                    >
                      <dt className="capitalize text-gray-500">{platform}</dt>
                      <dd className="font-medium">{(views as number).toLocaleString()}</dd>
                    </div>
                  )
                )}
              </dl>
            </div>
          )}

          {summary.creators?.length > 0 && (
            <div className="card overflow-hidden">
              <div className="p-6 border-b border-gray-100">
                <h2 className="text-base font-semibold text-gray-800">
                  Creator Performance
                </h2>
              </div>
              <table className="min-w-full divide-y divide-gray-100">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="table-header">Creator</th>
                    <th className="table-header">Published Clips</th>
                    <th className="table-header">Avg Views</th>
                    <th className="table-header">Avg Likes</th>
                    <th className="table-header">Avg Completion</th>
                    <th className="table-header">Top Clip Views</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {summary.creators.map((c: any) => (
                    <tr key={c.creator_id} className="hover:bg-gray-50">
                      <td className="table-cell font-medium text-gray-900">
                        {c.creator_name}
                      </td>
                      <td className="table-cell text-center">
                        {c.total_published_clips}
                      </td>
                      <td className="table-cell">
                        {c.avg_views.toFixed(0)}
                      </td>
                      <td className="table-cell">
                        {c.avg_likes.toFixed(0)}
                      </td>
                      <td className="table-cell">
                        {c.avg_completion_rate != null
                          ? `${(c.avg_completion_rate * 100).toFixed(1)}%`
                          : '—'}
                      </td>
                      <td className="table-cell">
                        {c.top_clip_views?.toLocaleString() ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-400">No analytics data available.</p>
      )}
    </div>
  );
}
