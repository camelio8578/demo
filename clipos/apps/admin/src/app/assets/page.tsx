'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';

export default function AssetsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['assets'],
    queryFn: () => api.get('/api/v1/assets').then((r) => r.data),
  });

  const assets = data?.items ?? data ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Rendered Assets</h1>

      <div className="card overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-400">Loading assets...</p>
        ) : error ? (
          <p className="p-6 text-sm text-red-500">Failed to load assets.</p>
        ) : assets.length === 0 ? (
          <p className="p-6 text-sm text-gray-400">No rendered assets yet.</p>
        ) : (
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="table-header">ID</th>
                <th className="table-header">Status</th>
                <th className="table-header">Resolution</th>
                <th className="table-header">Duration</th>
                <th className="table-header">Size</th>
                <th className="table-header">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {assets.map((a: any) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="table-cell font-mono text-xs text-gray-600">
                    {a.id.slice(0, 8)}…
                  </td>
                  <td className="table-cell">
                    <StatusBadge status={a.status} />
                  </td>
                  <td className="table-cell">{a.resolution ?? '—'}</td>
                  <td className="table-cell">
                    {a.duration_seconds
                      ? `${a.duration_seconds.toFixed(1)}s`
                      : '—'}
                  </td>
                  <td className="table-cell">
                    {a.file_size_bytes
                      ? `${(a.file_size_bytes / 1024 / 1024).toFixed(1)} MB`
                      : '—'}
                  </td>
                  <td className="table-cell text-gray-500">
                    {new Date(a.created_at).toLocaleDateString()}
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
