import clsx from 'clsx'

interface RiskFlagProps {
  flag: string
}

const FLAG_CONFIG: Record<string, { label: string; className: string; showIcon: boolean }> = {
  REQUIRES_LEGAL_REVIEW: {
    label: 'Requires Legal Review',
    className: 'bg-red-100 text-red-800 border border-red-300',
    showIcon: true,
  },
  high: {
    label: 'High Risk',
    className: 'bg-orange-100 text-orange-800',
    showIcon: false,
  },
  medium: {
    label: 'Medium Risk',
    className: 'bg-yellow-100 text-yellow-800',
    showIcon: false,
  },
  low: {
    label: 'Low Risk',
    className: 'bg-green-100 text-green-800',
    showIcon: false,
  },
}

export default function RiskFlag({ flag }: RiskFlagProps) {
  const config = FLAG_CONFIG[flag] ?? {
    label: flag,
    className: 'bg-gray-100 text-gray-600',
    showIcon: false,
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium',
        config.className
      )}
    >
      {config.showIcon && (
        <svg className="w-3.5 h-3.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
            clipRule="evenodd"
          />
        </svg>
      )}
      {config.label}
    </span>
  )
}
