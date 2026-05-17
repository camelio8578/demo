'use client';

import { useQuery } from '@tanstack/react-query';
import { getCreator } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function CreatorDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { data: creator, isLoading, error } = useQuery({
    queryKey: ['creator', params.id],
    queryFn: () => getCreator(params.id).then((r) => r.data),
  });

  if (isLoading) return <p className="text-sm text-gray-400">Loading...</p>;
  if (error || !creator)
    return <p className="text-sm text-red-500">Creator not found.</p>;

  return (
    <div>
      <Link
        href="/creators"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft size={14} /> Creators
      </Link>

      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{creator.name}</h1>
        <StatusBadge status={creator.status} size="md" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Details</h2>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">ID</dt>
              <dd className="font-mono text-xs text-gray-700">{creator.id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Slug</dt>
              <dd className="font-mono text-xs text-gray-700">{creator.slug}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Rights Profile</dt>
              <dd className="text-gray-700">
                {creator.rights_profile?.name ?? '—'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Created</dt>
              <dd className="text-gray-700">
                {new Date(creator.created_at).toLocaleString()}
              </dd>
            </div>
          </dl>
        </div>

        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Platform Accounts
          </h2>
          {creator.platform_accounts?.length ? (
            <ul className="space-y-2">
              {creator.platform_accounts.map((acc: any) => (
                <li
                  key={acc.id}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="capitalize text-gray-700">
                    {acc.platform}
                  </span>
                  <span className="text-gray-500 text-xs">
                    {acc.display_name ?? acc.platform_user_id ?? '—'}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">No platform accounts linked.</p>
          )}
        </div>

        <div className="card p-6 xl:col-span-2">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Monitored Sources
          </h2>
          {creator.monitored_sources?.length ? (
            <table className="min-w-full text-sm">
              <thead>
                <tr>
                  <th className="table-header">Platform</th>
                  <th className="table-header">URL</th>
                  <th className="table-header">Interval</th>
                  <th className="table-header">Last Polled</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {creator.monitored_sources.map((src: any) => (
                  <tr key={src.id}>
                    <td className="table-cell capitalize">{src.platform}</td>
                    <td className="table-cell text-xs font-mono max-w-xs truncate">
                      {src.source_url}
                    </td>
                    <td className="table-cell">{src.polling_interval_minutes}m</td>
                    <td className="table-cell text-gray-500">
                      {src.last_polled_at
                        ? new Date(src.last_polled_at).toLocaleString()
                        : 'Never'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-gray-400">No monitored sources.</p>
          )}
        </div>
      </div>
    </div>
  );
}
