'use client';

import { useQuery } from '@tanstack/react-query';
import { getVideos } from '@/lib/api';
import Link from 'next/link';
import StatusBadge from '@/components/StatusBadge';
import { ChevronRight } from 'lucide-react';

export default function VideosPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['videos'],
    queryFn: () => getVideos().then((r) => r.data),
  });

  const videos = data?.items ?? data ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Videos</h1>

      <div className="card overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-400">Loading videos...</p>
        ) : error ? (
          <p className="p-6 text-sm text-red-500">Failed to load videos.</p>
        ) : videos.length === 0 ? (
          <p className="p-6 text-sm text-gray-400">No videos found.</p>
        ) : (
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="table-header">Title</th>
                <th className="table-header">Status</th>
                <th className="table-header">Duration</th>
                <th className="table-header">Transcript</th>
                <th className="table-header">Created</th>
                <th className="table-header"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {videos.map((v: any) => {
                const transcript = v.transcripts?.[0];
                return (
                  <tr key={v.id} className="hover:bg-gray-50">
                    <td className="table-cell max-w-xs truncate font-medium text-gray-900">
                      {v.title ?? v.source_url}
                    </td>
                    <td className="table-cell">
                      <StatusBadge status={v.status} />
                    </td>
                    <td className="table-cell text-gray-500">
                      {v.duration_seconds
                        ? `${Math.round(v.duration_seconds)}s`
                        : '—'}
                    </td>
                    <td className="table-cell">
                      {transcript ? (
                        <StatusBadge status={transcript.status} />
                      ) : (
                        <span className="text-gray-400 text-xs">none</span>
                      )}
                    </td>
                    <td className="table-cell text-gray-500">
                      {new Date(v.created_at).toLocaleDateString()}
                    </td>
                    <td className="table-cell text-right">
                      <Link
                        href={`/videos/${v.id}`}
                        className="inline-flex items-center text-brand-600 hover:text-brand-700 text-sm"
                      >
                        View <ChevronRight size={14} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
