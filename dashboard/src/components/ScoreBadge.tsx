import clsx from 'clsx'

interface ScoreBadgeProps {
  score: number | null
}

export default function ScoreBadge({ score }: ScoreBadgeProps) {
  if (score === null) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
        —
      </span>
    )
  }

  const colorClass = clsx({
    'bg-green-100 text-green-800': score >= 80,
    'bg-blue-100 text-blue-800': score >= 60 && score < 80,
    'bg-yellow-100 text-yellow-800': score >= 40 && score < 60,
    'bg-red-100 text-red-800': score < 40,
  })

  return (
    <span className={clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', colorClass)}>
      {score}
    </span>
  )
}
