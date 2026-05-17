'use client';

import { useQuery } from '@tanstack/react-query';
import { getCreators } from '@/lib/api';
import Link from 'next/link';
import StatusBadge from '@/components/StatusBadge';
import { Plus, ChevronRight } from 'lucide-react';

export default function CreatorsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['creators'],
    queryFn: () => getCreators().then((r) => r.data),
  });

  const creators = data?.items ?? data ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Creators</h1>
        <button className="btn-primary">
          <Plus size={16} />
          Add Creator
        </button>
      </div>

      <div className="card overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-400">Loading creators...</p>
        ) : error ? (
          <p className="p-6 text-sm text-red-500">Failed to load creators.</p>
        ) : creators.length === 0 ? (
          <p className="p-6 text-sm text-gray-400">No creators found.</p>
        ) : (
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="table-header">Name</th>
                <th className="table-header">Slug</th>
                <th className="table-header">Status</th>
                <th className="table-header">Created</th>
                <th className="table-header"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {creators.map((c: any) => (
                <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                  <td className="table-cell font-medium text-gray-900">
                    {c.name}
                  </td>
                  <td className="table-cell text-gray-500 font-mono text-xs">
                    {c.slug}
                  </td>
                  <td className="table-cell">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="table-cell text-gray-500">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                  <td className="table-cell text-right">
                    <Link
                      href={`/creators/${c.id}`}
                      className="inline-flex items-center text-brand-600 hover:text-brand-700 text-sm"
                    >
                      View <ChevronRight size={14} />
                    </Link>
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
