import { clsx } from 'clsx';

interface SignalScore {
  label: string;
  value: number;
  max?: number;
}

interface Props {
  totalScore: number;
  signals?: SignalScore[];
}

function BarRow({ label, value, max = 1 }: SignalScore) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const color =
    pct >= 75
      ? 'bg-green-500'
      : pct >= 50
      ? 'bg-yellow-400'
      : pct >= 25
      ? 'bg-orange-400'
      : 'bg-red-400';

  return (
    <div className="flex items-center gap-3">
      <span className="w-36 text-xs text-gray-500 shrink-0 truncate">{label}</span>
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right text-xs text-gray-600 font-mono">
        {value.toFixed(2)}
      </span>
    </div>
  );
}

export default function ScoreBar({ totalScore, signals }: Props) {
  const totalPct = Math.min(100, Math.round(totalScore * 100));
  const totalColor =
    totalPct >= 75
      ? 'text-green-600'
      : totalPct >= 50
      ? 'text-yellow-600'
      : 'text-red-500';

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">Total Score</span>
        <span className={clsx('text-lg font-bold tabular-nums', totalColor)}>
          {(totalScore * 100).toFixed(0)}%
        </span>
      </div>

      <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={clsx(
            'h-full rounded-full transition-all',
            totalPct >= 75
              ? 'bg-green-500'
              : totalPct >= 50
              ? 'bg-yellow-400'
              : 'bg-red-400'
          )}
          style={{ width: `${totalPct}%` }}
        />
      </div>

      {signals && signals.length > 0 && (
        <div className="mt-4 space-y-2 border-t border-gray-100 pt-3">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
            Signal Breakdown
          </p>
          {signals.map((sig) => (
            <BarRow key={sig.label} {...sig} />
          ))}
        </div>
      )}
    </div>
  );
}
