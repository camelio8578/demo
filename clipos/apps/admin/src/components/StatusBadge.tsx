import { clsx } from 'clsx';

const STATUS_COLORS: Record<string, string> = {
  // Creator
  active: 'bg-green-100 text-green-800',
  paused: 'bg-yellow-100 text-yellow-800',
  blocked: 'bg-red-100 text-red-800',

  // Video / Asset
  discovered: 'bg-blue-100 text-blue-800',
  downloading: 'bg-blue-200 text-blue-900',
  downloaded: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  pending: 'bg-gray-100 text-gray-700',
  processing: 'bg-yellow-100 text-yellow-800',
  completed: 'bg-green-100 text-green-800',
  rendering: 'bg-blue-100 text-blue-800',

  // Candidate
  candidate: 'bg-gray-100 text-gray-700',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  rendered: 'bg-purple-100 text-purple-800',

  // Publishing
  queued: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  published: 'bg-green-100 text-green-800',
  cancelled: 'bg-gray-200 text-gray-600',

  // Review
  escalated: 'bg-orange-100 text-orange-800',
  in_review: 'bg-blue-100 text-blue-800',

  // Risk
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
};

interface Props {
  status: string;
  size?: 'sm' | 'md';
}

export default function StatusBadge({ status, size = 'sm' }: Props) {
  const color = STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-600';
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm',
        color
      )}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}
