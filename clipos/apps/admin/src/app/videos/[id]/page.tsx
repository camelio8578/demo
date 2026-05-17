'use client';

import { useQuery } from '@tanstack/react-query';
import { getVideo } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function VideoDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { data: video, isLoading, error } = useQuery({
    queryKey: ['video', params.id],
    queryFn: () => getVideo(params.id).then((r) => r.data),
  });

  if (isLoading) return <p className="text-sm text-gray-400">Loading...</p>;
  if (error || !video)
    return <p className="text-sm text-red-500">Video not found.</p>;

  const transcript = video.transcripts?.[0];
  const candidates = video.candidate_clips ?? [];

  return (
    <div>
      <Link
        href="/videos"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft size={14} /> Videos
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            {video.title ?? 'Untitled Video'}
          </h1>
          <a
            href={video.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-brand-600 hover:underline break-all"
          >
            {video.source_url}
          </a>
        </div>
        <StatusBadge status={video.status} size="md" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-3">
            Video Info
          </h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Duration</dt>
              <dd>{video.duration_seconds ? `${video.duration_seconds}s` : '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">File size</dt>
              <dd>
                {video.file_size_bytes
                  ? `${(video.file_size_bytes / 1024 / 1024).toFixed(1)} MB`
                  : '—'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Downloaded</dt>
              <dd>
                {video.downloaded_at
                  ? new Date(video.downloaded_at).toLocaleString()
                  : '—'}
              </dd>
            </div>
          </dl>
        </div>

        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-3">
            Transcript
          </h2>
          {transcript ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Status</span>
                <StatusBadge status={transcript.status} />
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Word count</span>
                <span>{transcript.word_count ?? '—'}</span>
              </div>
              {transcript.full_text && (
                <div className="mt-3">
                  <p className="text-xs text-gray-400 mb-1">Preview</p>
                  <p className="text-xs text-gray-700 bg-gray-50 rounded p-2 max-h-32 overflow-y-auto">
                    {transcript.full_text.slice(0, 500)}
                    {transcript.full_text.length > 500 ? '...' : ''}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400">No transcript available.</p>
          )}
        </div>
      </div>

      <div className="card p-6">
        <h2 className="text-base font-semibold text-gray-800 mb-4">
          Candidate Clips ({candidates.length})
        </h2>
        {candidates.length === 0 ? (
          <p className="text-sm text-gray-400">No candidate clips yet.</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                <th className="table-header">Start</th>
                <th className="table-header">End</th>
                <th className="table-header">Duration</th>
                <th className="table-header">Status</th>
                <th className="table-header">Text Preview</th>
                <th className="table-header"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {candidates.map((c: any) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="table-cell">{c.start_time?.toFixed(1)}s</td>
                  <td className="table-cell">{c.end_time?.toFixed(1)}s</td>
                  <td className="table-cell">{c.duration_seconds?.toFixed(1)}s</td>
                  <td className="table-cell">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="table-cell max-w-xs truncate text-gray-500">
                    {c.segment_text?.slice(0, 80) ?? '—'}
                  </td>
                  <td className="table-cell text-right">
                    <Link
                      href={`/candidates/${c.id}`}
                      className="text-brand-600 hover:underline text-xs"
                    >
                      Detail
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
