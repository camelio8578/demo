'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getCandidate,
  updateCandidateStatus,
  renderCandidate,
  generateCopy,
} from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import ScoreBar from '@/components/ScoreBar';
import Link from 'next/link';
import { ArrowLeft, CheckCircle, XCircle, Play, Wand2 } from 'lucide-react';

const SCORE_SIGNALS = [
  { key: 'speech_density', label: 'Speech Density' },
  { key: 'sentiment_score', label: 'Sentiment' },
  { key: 'hook_phrase_score', label: 'Hook Phrase' },
  { key: 'pause_burst_score', label: 'Pause / Burst' },
  { key: 'novelty_score', label: 'Novelty' },
  { key: 'completeness_score', label: 'Completeness' },
  { key: 'duration_fit_score', label: 'Duration Fit' },
  { key: 'risk_flag_score', label: 'Risk Flag' },
  { key: 'prior_performance_score', label: 'Prior Performance' },
];

export default function CandidateDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const qc = useQueryClient();

  const { data: candidate, isLoading, error } = useQuery({
    queryKey: ['candidate', params.id],
    queryFn: () => getCandidate(params.id).then((r) => r.data),
  });

  const approveMutation = useMutation({
    mutationFn: () => updateCandidateStatus(params.id, 'approved'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['candidate', params.id] }),
  });

  const rejectMutation = useMutation({
    mutationFn: () => updateCandidateStatus(params.id, 'rejected'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['candidate', params.id] }),
  });

  const renderMutation = useMutation({
    mutationFn: () => renderCandidate(params.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['candidate', params.id] }),
  });

  const copyMutation = useMutation({
    mutationFn: () => generateCopy(params.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['candidate', params.id] }),
  });

  if (isLoading) return <p className="text-sm text-gray-400">Loading...</p>;
  if (error || !candidate)
    return <p className="text-sm text-red-500">Candidate not found.</p>;

  const score = candidate.scores?.[0];
  const signals = score
    ? SCORE_SIGNALS.map(({ key, label }) => ({
        label,
        value: score[key] ?? 0,
        max: 1,
      }))
    : [];

  const assets = candidate.rendered_assets ?? [];
  const copyVariants = candidate.copy_variants ?? [];

  return (
    <div>
      <Link
        href="/candidates"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
      >
        <ArrowLeft size={14} /> Candidates
      </Link>

      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-xl font-bold text-gray-900">Candidate Clip</h1>
        <StatusBadge status={candidate.status} size="md" />
      </div>

      <div className="flex gap-3 mb-6">
        <button
          onClick={() => approveMutation.mutate()}
          disabled={approveMutation.isPending || candidate.status === 'approved'}
          className="btn-primary"
        >
          <CheckCircle size={14} /> Approve
        </button>
        <button
          onClick={() => rejectMutation.mutate()}
          disabled={rejectMutation.isPending || candidate.status === 'rejected'}
          className="btn-danger"
        >
          <XCircle size={14} /> Reject
        </button>
        <button
          onClick={() => renderMutation.mutate()}
          disabled={renderMutation.isPending}
          className="btn-secondary"
        >
          <Play size={14} /> Render
        </button>
        <button
          onClick={() => copyMutation.mutate()}
          disabled={copyMutation.isPending}
          className="btn-secondary"
        >
          <Wand2 size={14} /> Generate Copy
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Clip Info
          </h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Start</dt>
              <dd>{candidate.start_time?.toFixed(2)}s</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">End</dt>
              <dd>{candidate.end_time?.toFixed(2)}s</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Duration</dt>
              <dd>{candidate.duration_seconds?.toFixed(2)}s</dd>
            </div>
          </dl>
          {candidate.segment_text && (
            <div className="mt-4">
              <p className="text-xs text-gray-400 mb-1">Transcript Segment</p>
              <p className="text-xs text-gray-700 bg-gray-50 rounded p-3 leading-relaxed">
                {candidate.segment_text}
              </p>
            </div>
          )}
        </div>

        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Score Breakdown
          </h2>
          {score ? (
            <ScoreBar totalScore={score.total_score} signals={signals} />
          ) : (
            <p className="text-sm text-gray-400">No score data available.</p>
          )}
        </div>
      </div>

      {assets.length > 0 && (
        <div className="card p-6 mb-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Rendered Assets ({assets.length})
          </h2>
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                <th className="table-header">Status</th>
                <th className="table-header">Resolution</th>
                <th className="table-header">Duration</th>
                <th className="table-header">Size</th>
                <th className="table-header">Path</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {assets.map((a: any) => (
                <tr key={a.id}>
                  <td className="table-cell">
                    <StatusBadge status={a.status} />
                  </td>
                  <td className="table-cell">{a.resolution ?? '—'}</td>
                  <td className="table-cell">
                    {a.duration_seconds?.toFixed(1)}s
                  </td>
                  <td className="table-cell">
                    {a.file_size_bytes
                      ? `${(a.file_size_bytes / 1024 / 1024).toFixed(1)} MB`
                      : '—'}
                  </td>
                  <td className="table-cell font-mono text-xs text-gray-500 max-w-xs truncate">
                    {a.output_path ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {copyVariants.length > 0 && (
        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Copy Variants ({copyVariants.length})
          </h2>
          <div className="space-y-4">
            {copyVariants.map((v: any) => (
              <div
                key={v.id}
                className="border border-gray-100 rounded-lg p-4 text-sm"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="capitalize font-medium text-gray-700">
                    {v.platform}
                  </span>
                  <span className="text-gray-400 text-xs">
                    variant #{v.variant_index}
                  </span>
                </div>
                {v.hook && (
                  <p className="font-medium text-gray-900 mb-1">{v.hook}</p>
                )}
                {v.title && (
                  <p className="text-gray-700 mb-1">
                    <span className="text-gray-400 text-xs">Title: </span>
                    {v.title}
                  </p>
                )}
                {v.caption && (
                  <p className="text-gray-600 text-xs mt-1">{v.caption}</p>
                )}
                {v.hashtags && (
                  <p className="text-brand-600 text-xs mt-1">
                    {(v.hashtags as string[]).map((h) => `#${h}`).join(' ')}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
