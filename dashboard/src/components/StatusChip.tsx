import clsx from 'clsx'

interface StatusChipProps {
  status: string
}

const STATUS_CLASSES: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  reviewed: 'bg-blue-100 text-blue-800',
  qualified: 'bg-green-100 text-green-800',
  disqualified: 'bg-red-100 text-red-800',
  archived: 'bg-gray-100 text-gray-500',
  none: 'bg-gray-100 text-gray-500',
  drafted: 'bg-blue-100 text-blue-800',
  sent: 'bg-indigo-100 text-indigo-800',
  responded: 'bg-teal-100 text-teal-800',
  engaged: 'bg-green-100 text-green-800',
  closed: 'bg-gray-100 text-gray-500',
}

export default function StatusChip({ status }: StatusChipProps) {
  const className = STATUS_CLASSES[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize',
        className
      )}
    >
      {status}
    </span>
  )
}
