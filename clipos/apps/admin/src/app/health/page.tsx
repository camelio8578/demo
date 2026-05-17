'use client';

import { useQuery } from '@tanstack/react-query';
import { getHealth, getWorkerHealth, getQueueStatus } from '@/lib/api';
import { CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react';

function HealthRow({
  label,
  status,
  detail,
}: {
  label: string;
  status: 'ok' | 'error' | 'unknown';
  detail?: string;
}) {
  const icon =
    status === 'ok' ? (
      <CheckCircle size={16} className="text-green-500" />
    ) : status === 'error' ? (
      <XCircle size={16} className="text-red-500" />
    ) : (
      <AlertCircle size={16} className="text-yellow-500" />
    );

  return (
    <div className="flex items-center gap-3 py-3">
      {icon}
      <span className="text-sm font-medium text-gray-800 w-24">{label}</span>
      <span
        className={`text-sm ${
          status === 'ok'
            ? 'text-green-600'
            : status === 'error'
            ? 'text-red-500'
            : 'text-yellow-600'
        }`}
      >
        {status === 'ok' ? 'OK' : status === 'error' ? 'ERROR' : 'Unknown'}
      </span>
      {detail && (
        <span className="text-xs text-gray-400 ml-2">{detail}</span>
      )}
    </div>
  );
}

export default function HealthPage() {
  const {
    data: health,
    isLoading: healthLoading,
    error: healthError,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['health'],
    queryFn: () => getHealth().then((r) => r.data),
    refetchInterval: 15_000,
  });

  const { data: workers } = useQuery({
    queryKey: ['worker-health'],
    queryFn: () => getWorkerHealth().then((r) => r.data),
    refetchInterval: 15_000,
  });

  const { data: queueStatus } = useQuery({
    queryKey: ['queue-status'],
    queryFn: () => getQueueStatus().then((r) => r.data),
    refetchInterval: 15_000,
  });

  const apiStatus = healthError ? 'error' : health ? 'ok' : 'unknown';
  const dbStatus =
    health?.database === 'ok'
      ? 'ok'
      : health?.database
      ? 'error'
      : ('unknown' as const);
  const redisStatus =
    health?.redis === 'ok'
      ? 'ok'
      : health?.redis
      ? 'error'
      : ('unknown' as const);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">System Health</h1>
        <button
          onClick={() => refetchHealth()}
          className="btn-secondary"
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-2">
            Core Services
          </h2>
          <div className="divide-y divide-gray-100">
            <HealthRow
              label="API"
              status={apiStatus}
              detail={health?.version ?? undefined}
            />
            <HealthRow
              label="Database"
              status={dbStatus}
              detail={health?.database}
            />
            <HealthRow
              label="Redis"
              status={redisStatus}
              detail={health?.redis}
            />
          </div>
        </div>

        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Queue Depths
          </h2>
          {queueStatus ? (
            <dl className="space-y-2">
              {Object.entries(queueStatus.queued_jobs ?? {}).map(
                ([queue, count]) => (
                  <div key={queue} className="flex justify-between text-sm">
                    <dt className="text-gray-500 capitalize">{queue}</dt>
                    <dd
                      className={`font-medium ${
                        (count as number) > 10
                          ? 'text-orange-600'
                          : 'text-gray-900'
                      }`}
                    >
                      {count as number}
                    </dd>
                  </div>
                )
              )}
            </dl>
          ) : (
            <p className="text-sm text-gray-400">Queue info unavailable.</p>
          )}
        </div>

        {workers && (
          <div className="card p-6 xl:col-span-2">
            <h2 className="text-base font-semibold text-gray-800 mb-4">
              Active Workers
            </h2>
            {Object.keys(workers).length === 0 ? (
              <p className="text-sm text-gray-400">
                No active workers detected.
              </p>
            ) : (
              <dl className="space-y-2">
                {Object.entries(workers).map(([name, info]: [string, any]) => (
                  <div key={name} className="flex justify-between text-sm">
                    <dt className="text-gray-700 font-mono text-xs">{name}</dt>
                    <dd className="text-gray-500">
                      {typeof info === 'object'
                        ? JSON.stringify(info)
                        : String(info)}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
