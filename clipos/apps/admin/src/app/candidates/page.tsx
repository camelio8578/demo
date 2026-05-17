'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getReviewQueue, updateCandidateStatus } from '@/lib/api';
import StatusBadge from '@/components/StatusBadge';
import ScoreBar from '@/components/ScoreBar';
import Link from 'next/link';
import { CheckCircle, XCircle, ChevronRight } from 'lucide-react';

export default function CandidatesPage() {
  const qc = useQueryClient();

  const { data: queue, isLoading, error } = useQuery({
    queryKey: ['review-queue'],
    queryFn: () => getReviewQueue().then((r) => r.data),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => updateCandidateStatus(id, 'approved'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['review-queue'] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => updateCandidateStatus(id, 'rejected'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['review-queue'] }),
  });

  const candidates = queue ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Candidate Review Queue
      </h1>

      {isLoading ? (
        <p className="text-sm text-gray-400">Loading queue...</p>
      ) : error ? (
        <p className="text-sm text-red-500">Failed to load review queue.</p>
      ) : candidates.length === 0 ? (
        <div className="card p-12 text-center text-gray-400">
          <p className="text-lg">Queue empty — no candidates to review.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {candidates.map((c: any) => {
            const score = c.scores?.[0];
            const totalScore = score?.total_score ?? 0;

            return (
              <div key={c.id} className="card p-6">
                <div className="flex items-start gap-6">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <StatusBadge status={c.status} />
                      <span className="text-xs text-gray-400 font-mono">
                        {c.id}
                      </span>
                    </div>

                    <p className="text-sm text-gray-700 mb-3 line-clamp-2">
                      {c.segment_text ?? 'No transcript segment.'}
                    </p>

                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>{c.start_time?.toFixed(1)}s — {c.end_time?.toFixed(1)}s</span>
                      <span>{c.duration_seconds?.toFixed(1)}s duration</span>
                    </div>
                  </div>

                  <div className="w-56 shrink-0">
                    <ScoreBar totalScore={totalScore} />
                  </div>

                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => approveMutation.mutate(c.id)}
                      disabled={approveMutation.isPending}
                      className="btn-primary"
                    >
                      <CheckCircle size={14} />
                      Approve
                    </button>
                    <button
                      onClick={() => rejectMutation.mutate(c.id)}
                      disabled={rejectMutation.isPending}
                      className="btn-danger"
                    >
                      <XCircle size={14} />
                      Reject
                    </button>
                    <Link
                      href={`/candidates/${c.id}`}
                      className="btn-secondary justify-center"
                    >
                      Detail <ChevronRight size={14} />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
